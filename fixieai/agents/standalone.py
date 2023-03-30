import inspect
from typing import Callable, List, Optional

import fastapi

from fixieai.agents import agent_base
from fixieai.agents import api
from fixieai.agents import metadata
from fixieai.agents import oauth
from fixieai.agents import utils


class StandaloneAgent(agent_base.AgentBase):
    """An agent that handles queries directly.

    To make a StandaloneAgent, pass a function with the following signature

    def handle(query: fixieai.Message) -> ReturnType:
            ...

    where ReturnType is one of `str`, `fixieai.Message`, or `fixie.AgentResponse`.
    """

    def __init__(
        self,
        handle_message: Callable,
        sample_queries: Optional[List[str]] = None,
        oauth_params: Optional[oauth.OAuthParams] = None,
    ):
        super().__init__(oauth_params)

        self._handle_message = handle_message
        self._sample_queries = sample_queries
        utils.validate_registered_pyfunc(handle_message, self)

    def metadata(self) -> metadata.Metadata:
        return metadata.StandaloneAgentMetadata(sample_queries=self._sample_queries)

    def validate(self):
        pass

    def api_router(self) -> fastapi.APIRouter:
        router = super().api_router()
        router.add_api_route("/", self._serve_query, methods=["POST"])
        return router

    def _serve_query(
        self,
        query: api.AgentQuery,
        credentials: fastapi.security.HTTPAuthorizationCredentials = fastapi.Depends(
            fastapi.security.HTTPBearer()
        ),
    ) -> api.AgentResponse:
        """Verifies the request is a valid request from Fixie, and dispatches it to
        the appropriate function.
        """
        token_claims = self.validate_token(credentials)

        kwargs = self.get_func_kwargs(
            query,
            token_claims,
            inspect.signature(self._handle_message).parameters.keys(),
        )
        output = self._handle_message(**kwargs)
        try:
            return api.AgentResponse.from_value(output)
        except TypeError:
            raise TypeError(f"Query returned unexpected output of type {type(output)}.")
