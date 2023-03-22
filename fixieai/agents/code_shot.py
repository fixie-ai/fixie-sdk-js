from __future__ import annotations

import dataclasses
import functools
import inspect
import json
import re
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import fastapi
import jwt
import requests
import uvicorn
import yaml
from pydantic import dataclasses as pydantic_dataclasses

from fixieai import constants
from fixieai.agents import api
from fixieai.agents import corpora
from fixieai.agents import oauth
from fixieai.agents import user_storage
from fixieai.agents import utils

# Regex that controls what Func names are allowed.
ACCEPTED_FUNC_NAMES = re.compile(r"^\w+$")

# The JWT claim containing the agent ID
_AGENT_ID_JWT_CLAIM = "aid"


@pydantic_dataclasses.dataclass
class AgentMetadata:
    """Metadata for a Fixie CodeShot Agent.

    This will get sent to the Fixie platform upon handshake.
    """

    base_prompt: str
    few_shots: List[str]
    corpora: Optional[List[corpora.DocumentCorpus]] = None
    conversational: bool = False


class CodeShotAgent:
    """A CodeShot agent.

    To make a CodeShot agent, simply pass a BASE_PROMPT and FEW_SHOTS:

        BASE_PROMPT = "A summary of what this agent does; how it does it; and its
        personality"

        FEW_SHOTS = '''
        Q: <Sample query that this agent supports>
        A: <Desired response for this query>

        Q: <Another sample query>
        A: <Desired response for this query>
        '''

        agent = CodeShotAgent(BASE_PROMPT, FEW_SHOTS)

    You can have FEW_SHOTS as a single string of all your few-shots separated by 2 new
    lines, or as an explicit list of one few-shot per index.

    Your few-shots may reach out to other Agents in the fixie ecosystem by
    "Ask Agent[agent_id]: <query to pass>", or reach out to some python functions
    by "Ask Func[func_name]: <query to pass>".

    There are a series of default runtime `Func`s provided by the platform available for
    your agents to consume. For a full list of default runtime `Func`s, refer to:
        http://docs.fixie.ai/XXX

    You may also need to write your own python functions here to be consumed by your
    agent. To make a function accessible by an agent, you'd need to register it by
    `@agent.register_func`. Example:

        @agent.register_func
        def func_name(query: fixieai.Message) -> ReturnType:
            ...

        , where ReturnType is one of `str`, `fixieai.Message`, or `fixie.AgentResponse`.

    Note that in the above, we are using the decorator `@agent.register_func` to
    register this function with the agent instance we just created.

    To check out the default `Func`s that are provided in Fixie, see:
        http://docs.fixie.ai/XXX

    """

    def __init__(
        self,
        base_prompt: str,
        few_shots: Union[str, List[str]],
        corpora: Optional[List[corpora.DocumentCorpus]] = None,
        conversational: bool = False,
        oauth_params: Optional[oauth.OAuthParams] = None,
    ):
        if isinstance(few_shots, str):
            few_shots = _split_few_shots(few_shots)

        self.base_prompt = base_prompt
        self.few_shots = few_shots
        self.corpora = corpora
        self.conversational = conversational
        self.oauth_params = oauth_params
        self._funcs: Dict[str, Callable] = {}
        self._jwks_client = jwt.PyJWKClient(constants.FIXIE_JWKS_URL)

        if oauth_params is not None:
            # Register default Funcs.
            self.register_func(_oauth)

        utils.strip_prompt_lines(self)

    def serve(
        self, agent_id: Optional[str] = None, host: str = "0.0.0.0", port: int = 8181
    ):
        """Starts serving the current agent at `{host}:{port}` via uvicorn.

        If agent_id is specified, this pings Fixie upon startup to fetch the latest prompt and fewshots.

        Args:
            agent_id: The qualified agent id (`username/handle`)
            host: The address to start listening at.
            port: The port number to start listening at.
        """
        uvicorn.run(self.app(agent_id), host=host, port=port)

    def app(self, agent_id: Optional[str] = None) -> fastapi.FastAPI:
        """Returns a fastapi.FastAPI application that serves the agent.

        If agent_id is specified, this pings Fixie upon startup to fetch the latest prompt and fewshots.

        Args:
            agent_id: The qualified agent id (`username/handle`)
        """
        fast_api = fastapi.FastAPI()
        fast_api.include_router(self.api_router())
        agent_id = agent_id
        if agent_id:
            fast_api.add_event_handler(
                "startup", functools.partial(_ping_fixie_async, agent_id)
            )
        return fast_api

    def api_router(self) -> fastapi.APIRouter:
        """Returns a fastapi.APIRouter object that serves the agent."""
        router = fastapi.APIRouter()
        router.add_api_route("/", self._handshake, methods=["GET"])
        router.add_api_route("/{func_name}", self._serve_func, methods=["POST"])
        return router

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

        if func_name is not None:
            if not ACCEPTED_FUNC_NAMES.fullmatch(func_name):
                raise ValueError(
                    f"Function names may only be alphanumerics, got {func_name!r}."
                )

        utils.validate_registered_pyfunc(func, self)
        name = func_name or func.__name__
        if name in self._funcs:
            raise ValueError(f"Func[{name}] is already registered with agent.")
        self._funcs[name] = func
        return func

    def _handshake(self) -> fastapi.Response:
        """Returns the agent's metadata in YAML format."""
        metadata = AgentMetadata(
            self.base_prompt, self.few_shots, self.corpora, self.conversational
        )
        yaml_content = yaml.dump(dataclasses.asdict(metadata))
        return fastapi.Response(yaml_content, media_type="application/yaml")

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
        token_claims = _VerifiedTokenClaims.from_token(
            credentials.credentials, self._jwks_client
        )
        if token_claims is None:
            raise fastapi.HTTPException(status_code=403, detail="Invalid token")
        elif (
            query.access_token is not None
            and query.access_token != credentials.credentials
        ):
            raise fastapi.HTTPException(status_code=403, detail="Mismatched tokens")
        else:
            query.access_token = credentials.credentials

        try:
            pyfunc = self._funcs[func_name]
        except KeyError:
            raise fastapi.HTTPException(
                status_code=404, detail=f"Func[{func_name}] doesn't exist"
            )
        kwargs = self._get_func_kwargs(
            query, token_claims, inspect.signature(pyfunc).parameters.keys()
        )
        output = pyfunc(**kwargs)
        try:
            return _wrap_with_agent_response(output)
        except TypeError:
            raise TypeError(
                f"Func[{func_name}] returned unexpected output of type {type(output)}."
            )

    def _get_func_kwargs(
        self,
        query: api.AgentQuery,
        token_claims: _VerifiedTokenClaims,
        arg_names: Iterable[str],
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        for arg_name in arg_names:
            if arg_name == "query":
                kwargs[arg_name] = query.message
            elif arg_name == "user_storage":
                kwargs[arg_name] = user_storage.UserStorage(
                    query, token_claims.agent_id
                )
            elif arg_name == "oauth_handler":
                assert self.oauth_params, "oauth_params is not set"
                kwargs[arg_name] = oauth.OAuthHandler(
                    self.oauth_params, query, token_claims.agent_id
                )
            else:
                raise ValueError(f"Found unknown argument {arg_name!r}.")
        return kwargs


@pydantic_dataclasses.dataclass
class _VerifiedTokenClaims:
    """Verified claims from an agent token."""

    agent_id: str

    @staticmethod
    def from_token(
        token: str, jwks_client: jwt.PyJWKClient
    ) -> Optional[_VerifiedTokenClaims]:
        try:
            public_key = jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                public_key.key,
                algorithms=["EdDSA"],
                audience=constants.FIXIE_AGENT_API_AUDIENCES,
            )
        except jwt.DecodeError:
            return None

        if _AGENT_ID_JWT_CLAIM not in claims or not isinstance(
            claims[_AGENT_ID_JWT_CLAIM], str
        ):
            # Agent id claim is required
            return None

        return _VerifiedTokenClaims(agent_id=claims[_AGENT_ID_JWT_CLAIM])


def _oauth(query: api.Message, oauth_handler: oauth.OAuthHandler) -> str:
    """Serves Func[_oauth] which is used upon auth redirect callback."""
    auth_request = json.loads(query.text)
    state = auth_request["state"]
    code = auth_request["code"]
    oauth_handler.authorize(state, code)
    return "Authorization successful!"


def _wrap_with_agent_response(
    value: Union[str, api.Message, api.AgentResponse]
) -> api.AgentResponse:
    if isinstance(value, str):
        return api.AgentResponse(api.Message(value))
    elif isinstance(value, api.Message):
        return api.AgentResponse(value)
    elif isinstance(value, api.AgentResponse):
        return value
    else:
        raise TypeError(f"Unexpected type to wrap: {type(value)}")


def _split_few_shots(few_shots: str) -> List[str]:
    """Split a long string of all few-shots into a list of few-shot strings."""
    # First, strip all lines to remove bad spaces.
    few_shots = "\n".join(line.strip() for line in few_shots.splitlines())
    # Then, split by "\n\nQ:".
    few_shot_splits = few_shots.split("\n\nQ:")
    few_shot_splits = [few_shot_splits[0]] + [
        "Q:" + few_shot for few_shot in few_shot_splits[1:]
    ]
    return few_shot_splits


def _ping_fixie_async(agent_id: str):
    """Asynchronously pings Fixie to refresh the given agent_id."""
    thread = threading.Thread(target=_ping_fixie_sync, args=(agent_id,))
    thread.start()


def _ping_fixie_sync(agent_id: str):
    # Pause a second to give the agent a moment to start up.
    time.sleep(1)
    response = requests.post(f"{constants.FIXIE_REFRESH_URL}/{agent_id}")
    response.raise_for_status()
