from __future__ import annotations

import abc
import dataclasses
import functools
import json
import os
import re
import warnings
from typing import Callable, Dict, Optional, TypeVar

import fastapi
import fastapi.security
import jwt
import starlette.responses
import uvicorn
import yaml

from fixieai import constants
from fixieai.agents import agent_func
from fixieai.agents import api
from fixieai.agents import corpora
from fixieai.agents import exceptions
from fixieai.agents import metadata as agent_metadata
from fixieai.agents import oauth
from fixieai.agents import token

# Regex that controls what Func names are allowed.
ACCEPTED_FUNC_NAMES = re.compile(r"^\w+$")

_RESPONSE_CHUNK_SIZE = 1024


class AgentBase(abc.ABC):
    """Base class for Fixie agents."""

    def __init__(
        self,
        oauth_params: Optional[oauth.OAuthParams] = None,
    ):
        self.oauth_params = oauth_params
        self._funcs: Dict[str, agent_func.AgentQueryFunc] = {}
        self._corpus_funcs: Dict[str, agent_func.AgentCorpusFunc] = {}
        self._jwks_client = jwt.PyJWKClient(constants.FIXIE_JWKS_URL)
        self._allowed_agent_id = os.getenv("FIXIE_ALLOWED_AGENT_ID")
        if self._allowed_agent_id is None:
            warnings.warn(
                "No allowed agent ID was specified, so your agent will accept requests intended for any agent. "
                "Ensure that the FIXIE_ALLOWED_AGENT_ID variable is set to correct this."
            )

        if oauth_params is not None:
            # Register default Funcs.
            self.register_func(_oauth)

    @abc.abstractmethod
    def metadata(self) -> agent_metadata.Metadata:
        """Returns metadata about how the agent should be interacted with."""

    @abc.abstractmethod
    def validate(self):
        """Performs any validation after all funcs are registered."""

    def serve(self, host: str = "0.0.0.0", port: int = 8181):
        """Starts serving the current agent at `{host}:{port}` via uvicorn.

        Args:
            host: The address to start listening at.
            port: The port number to start listening at.
        """
        uvicorn.run(self.app(), host=host, port=port)

    def app(self) -> fastapi.FastAPI:
        """Returns a fastapi.FastAPI application that serves the agent."""
        fast_api = fastapi.FastAPI()
        fast_api.include_router(self.api_router())
        fast_api.add_exception_handler(
            exceptions.AgentException, exceptions.AgentException.fastapi_handler
        )

        return fast_api

    def api_router(self) -> fastapi.APIRouter:
        """Returns a fastapi.APIRouter object that serves the agent."""
        router = fastapi.APIRouter()
        router.add_api_route("/", self._handshake, methods=["GET"])
        router.add_api_route("/{func_name}", self._serve_func, methods=["POST"])
        router.add_api_route(
            "/corpus/{corpus_func_name}", self._serve_corpus_func, methods=["POST"]
        )
        return router

    def is_valid_func_name(self, func_name: str) -> bool:
        """Indicates if the given func name is valid (either registered or built-in).

        Args:
            func_name: The func name to check
        """
        return func_name in self._funcs or func_name.startswith("fixie_")

    def register_func(
        self, func: Optional[Callable] = None, *, func_name: Optional[str] = None
    ) -> Callable:
        """A function decorator to register `Func`s with this agent.

        This decorator will not change the callable itself.

        Usage:

            agent = CodeShotAgent(base_prompt, few_shots)

            @agent.register_func
            def func(query):
                ...

        Optional Decorator Args:
            func_name: Optional function name to register this function by. If unset,
                the function name will be used.
        """
        if func is None:
            # Func is not passed in. It's the decorator being created.
            return functools.partial(self.register_func, func_name=func_name)
        non_null_func: Callable = func

        AgentBase._register_func_internal(
            func,
            func_name,
            self._funcs,
            lambda: agent_func.AgentQueryFunc.create(
                non_null_func,
                self.oauth_params,
                default_message_type=api.Message,
                allow_generator=False,
            ),
        )
        return func

    def register_corpus_func(
        self,
        func: Optional[
            Callable[[corpora.CorpusRequest], corpora.CorpusResponse]
        ] = None,
        *,
        func_name: Optional[str] = None,
    ) -> Callable:
        """A function decorator to register `Func`s used for loading a custom
        corpus with this agent.

        This decorator will not change the callable itself.

        Usage:

            agent = CodeShotAgent(base_prompt, few_shots)

            @agent.register_corpus_func
            def func(request: CorpusRequest) -> CorpusResponse:
                ...

        Optional Decorator Args:
            func_name: Optional function name to register this function by. If unset,
                the function name will be used.
        """
        if func is None:
            # Func is not passed in. It's the decorator being created.
            return functools.partial(self.register_corpus_func, func_name=func_name)
        non_null_func: Callable[[corpora.CorpusRequest], corpora.CorpusResponse] = func

        AgentBase._register_func_internal(
            func,
            func_name,
            self._corpus_funcs,
            lambda: agent_func.AgentCorpusFunc.create(non_null_func),
        )
        return func

    T = TypeVar("T")

    @staticmethod
    def _register_func_internal(
        func: Callable,
        func_name: Optional[str],
        registry: Dict[str, T],
        create: Callable[[], T],
    ):
        if func_name is not None:
            if not ACCEPTED_FUNC_NAMES.fullmatch(func_name):
                raise ValueError(
                    f"Function names may only be alphanumerics, got {func_name!r}."
                )
        else:
            func_name = func.__name__

        if func_name in registry:
            raise ValueError(f"Func[{func_name}] is already registered with agent.")

        registry[func_name] = create()

    def _handshake(
        self,
        credentials: fastapi.security.HTTPAuthorizationCredentials = fastapi.Depends(
            fastapi.security.HTTPBearer()
        ),
    ) -> fastapi.Response:
        """Returns the agent's metadata in YAML format."""
        token_claims = token.VerifiedTokenClaims.from_token(
            credentials.credentials, self._jwks_client, self._allowed_agent_id
        )
        if token_claims is None:
            raise fastapi.HTTPException(status_code=403, detail="Invalid token")

        metadata = self.metadata()
        yaml_content = yaml.dump(dataclasses.asdict(metadata))

        # Use a streaming response because metadata can be very large.
        chunks = (
            yaml_content[start : start + _RESPONSE_CHUNK_SIZE]
            for start in range(0, len(yaml_content), _RESPONSE_CHUNK_SIZE)
        )
        return starlette.responses.StreamingResponse(
            chunks,
            media_type="application/yaml",
        )

    def _serve_func(
        self,
        func_name: str,
        query: api.AgentQuery,
        credentials: fastapi.security.HTTPAuthorizationCredentials = fastapi.Depends(
            fastapi.security.HTTPBearer()
        ),
    ) -> api.AgentResponse:
        """Verifies the request is a valid request from Fixie, and dispatches it to
        the appropriate function.
        """
        token_claims = self._check_credentials(credentials)

        try:
            pyfunc = self._funcs[func_name]
        except KeyError:
            raise exceptions.AgentException(
                response_message=f"I'm sorry, Func[{func_name}] is not defined.",
                error_code="ERR_FUNC_NOT_DEFINED",
                error_message="The function was not defined.",
                http_status_code=404,
                func_name=func_name,
                available_funcs=list(self._funcs.keys()),
            )

        output = pyfunc(query, token_claims)

        # Streaming not allowed for funcs (yet).
        return next(iter(output))

    def _serve_corpus_func(
        self,
        corpus_func_name: str,
        request: corpora.CorpusRequest,
        credentials: fastapi.security.HTTPAuthorizationCredentials = fastapi.Depends(
            fastapi.security.HTTPBearer()
        ),
    ) -> fastapi.responses.JSONResponse:
        """Verifies the request is a valid request from Fixie, and dispatches it to
        the appropriate corpus function.
        """
        token_claims = self._check_credentials(credentials)

        try:
            pyfunc = self._corpus_funcs[corpus_func_name]
        except KeyError:
            raise exceptions.AgentException(
                response_message=f"I'm sorry, corpus func[{corpus_func_name}] is not defined.",
                error_code="ERR_FUNC_NOT_DEFINED",
                error_message="The function was not defined.",
                http_status_code=404,
                func_name=corpus_func_name,
                available_funcs=list(self._corpus_funcs.keys()),
            )

        output = pyfunc(request, token_claims)

        result = next(iter(output))
        # Use dataclasses_json instead of FastAPI's default json encoder. This
        # allows us to use our own bytes encoder instead of the default, which
        # always uses utf-8 and therefore wouldn't allow some characters.
        return fastapi.responses.JSONResponse(result.to_dict())

    def _check_credentials(
        self, credentials: fastapi.security.HTTPAuthorizationCredentials
    ) -> token.VerifiedTokenClaims:
        token_claims = token.VerifiedTokenClaims.from_token(
            credentials.credentials, self._jwks_client, self._allowed_agent_id
        )
        if token_claims is None:
            raise fastapi.HTTPException(status_code=403, detail="Invalid token")
        return token_claims


def _oauth(query: api.Message, oauth_handler: oauth.OAuthHandler) -> str:
    """Serves Func[_oauth] which is used upon auth redirect callback."""
    auth_request = json.loads(query.text)
    state = auth_request["state"]
    code = auth_request["code"]
    oauth_handler.authorize(state, code)
    return "Authorization successful!"
