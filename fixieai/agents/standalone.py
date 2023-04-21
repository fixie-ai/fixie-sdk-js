import dataclasses
import json
from typing import Callable, List, Optional

import fastapi

from fixieai.agents import agent_base
from fixieai.agents import agent_func
from fixieai.agents import api
from fixieai.agents import metadata
from fixieai.agents import oauth


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

        if isinstance(handle_message, agent_func.AgentFunc):
            self._handle_message: agent_func.AgentFunc = handle_message
        else:
            self._handle_message = agent_func.AgentFunc.create(
                handle_message,
                oauth_params,
                default_message_type=api.Message,
                allow_generator=True,
            )
        self._sample_queries = sample_queries

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
    ) -> fastapi.responses.Response:
        """Verifies the request is a valid request from Fixie, and dispatches it to
        the previously specified `handle_message` function. Depending on the return
        value of that function, either a single or a streaming response is returned.
        """
        token_claims = self.validate_token_and_update_query_access_token(
            query, credentials
        )

        output = self._handle_message(query, token_claims.agent_id)
        return fastapi.responses.StreamingResponse(
            (json.dumps(dataclasses.asdict(resp)) + "\n" for resp in output),
            media_type="application/json",
        )
