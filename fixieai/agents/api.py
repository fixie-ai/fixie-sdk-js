"""This module holds objects that represent the API interface by which Agents talk to
Fixie ecosystem."""

from __future__ import annotations

import dataclasses
from typing import Dict, Optional

from pydantic import dataclasses as pydantic_dataclasses


@pydantic_dataclasses.dataclass
class Embed:
    """An Embed represents a binary object attached to a Message."""

    # The MIME content type of the object, e.g., "image/png" or "application/json".
    content_type: str

    # A public URL where the object can be downloaded. The Embed API can be used to
    # upload an Embed object to Fixie and generate a URL.
    uri: str


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
class AgentResponse:
    """A response message from an Agent."""

    # The text of the response message.
    message: Message
