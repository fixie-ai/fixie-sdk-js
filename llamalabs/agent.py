from __future__ import annotations

import enum
from typing import Generator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class Embed(BaseModel):
    """An Embed represents a binary object attached to a Message."""

    # The MIME content type of the object, e.g., "image/png" or "application/json".
    content_type: str

    # A public URL where the object can be downloaded. The Embed API can be used to
    # upload an Embed object to Llama Labs and generate a URL.
    uri: str


class Message(BaseModel):
    """A Message represents a single message sent to a Llama Labs agent."""

    # The text of the message.
    text: str

    # A mapping of embed keys to Embed objects.
    embeds: dict[str, Embed] = {}


class AgentQuery(BaseModel):
    """A query sent to a Llama Labs agent."""

    # The contents of the query.
    message: Message

    # An access token associated with the user for whom this query was created.
    # Agents wishing to make queries to other agents, or to other Llama Labs services,
    # should carry this token in the query so that it can be tied back to the original
    # user.
    access_token: Optional[str] = None

    # The ID of the (human) user for whom this query was made. Agents should treat
    # this as an opaque string and not make any assumptions about its format, other
    # than that it uniquely identifies an end user.
    originating_user_id: Optional[str] = None

    # A session ID that can be used by agents to identify a given user's "session"
    # while interacting with the Llama Labs system. Agents should treat this as an
    # opaque string and not make any assumptions about its format, other than that
    # it uniquely identifies a session for a given user.
    session_id: Optional[str] = None


class AgentResponseType(enum.Enum):
    RESPONSE = "response"
    STATUS_GOT_QUERY = "status_got_query"
    STATUS_RESPONSE_READY = "status_response_ready"
    STATUS_MIDDLE_PROMPT = "status_middle_prompt"


class AgentResponse(BaseModel):
    message: str

    response_type: Optional[str]

    # The responding agent id, if different than the one that received the query.
    from_agent: Optional[str] = None


class Agent:
    def __init__(self):
        self.router = APIRouter()
        self.router.add_api_route("/", self._do_query, methods=["POST"])

    def _do_query(self, query: AgentQuery) -> StreamingResponse:
        # TODO(mdw): Add support for verifying query JWT.
        responses_it = self.query(query)
        bytes_it = (
            response.json().encode("utf-8") + b"\r\n" for response in responses_it
        )
        return StreamingResponse(bytes_it)

    def query(self, query: AgentQuery) -> Generator[AgentResponse, None, None]:
        raise NotImplemented
