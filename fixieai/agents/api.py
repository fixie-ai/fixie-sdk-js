"""This module holds objects that represent the API interface by which Agents talk to
Fixie ecosystem."""

from __future__ import annotations

import base64
import dataclasses
from typing import Dict, Generator, Optional

import requests
from pydantic import dataclasses as pydantic_dataclasses


@pydantic_dataclasses.dataclass
class Embed:
    """An Embed represents a binary object attached to a Message."""

    # The MIME content type of the object, e.g., "image/png" or "application/json".
    content_type: str

    # A public URL where the object can be downloaded. This can be a data URI.
    uri: str

    @property
    def content(self) -> bytes:
        """Retrieves the content for this Embed object."""
        if self.uri.startswith("data:"):
            return base64.b64decode(self.uri.split(",")[1])
        return requests.get(self.uri).content

    @content.setter
    def content(self, content: bytes):
        """Sets the content of the Embed object as a data URI."""
        self.uri = f"data:base64,{base64.b64encode(content).decode('utf-8')}"

    @property
    def text(self) -> str:
        """Retrieves the content of the Embed object as a string."""
        return self.content.decode("utf-8")

    @text.setter
    def text(self, text: str):
        """Sets the content of the Embed object as a string."""
        self.content = text.encode("utf-8")


@pydantic_dataclasses.dataclass
class Message:
    """A Message represents a single message sent to a Fixie agent."""

    # The text of the message.
    text: str

    # A mapping of embed keys to Embed objects.
    embeds: Dict[str, Embed] = dataclasses.field(default_factory=dict)


@pydantic_dataclasses.dataclass
class AgentQuery:
    """A standalone query sent to a Fixie agent."""

    # The contents of the query.
    message: Message

    # This is an access token associated with the user for whom this query was
    # created. Agents wishing to make queries to other agents, or to other
    # Fixie services, should carry this token in the query so that it
    # can be tied back to the original user.
    access_token: Optional[str] = None


@pydantic_dataclasses.dataclass
class AgentError:
    """An error that occurred in the process of generating a response."""

    # A code representing the error.
    code: str

    # A message describing the error that will be displayed to the user.
    message: str

    # Additional debugging context from the error.
    details: Optional[Dict]


@pydantic_dataclasses.dataclass
class AgentResponse:
    """A response message from an Agent."""

    # The text of the response message.
    message: Message

    # Error details, if an error occurred generating the response. Note that `message` should still be included,
    # but may indicate that an error occurred that prevented the agent from fully handling the request.
    error: Optional[AgentError] = None


AgentResponseGenerator = Generator[AgentResponse, None, None]
