from __future__ import annotations

import dataclasses
from typing import Optional

from pydantic import dataclasses as pydantic_dataclasses


@pydantic_dataclasses.dataclass
class Embed:
    """An Embed represents a binary object attached to a Message."""

    # The MIME content type of the object, e.g., "image/png" or "application/json".
    content_type: str

    # A public URL where the object can be downloaded. The Embed API can be used to
    # upload an Embed object to Llama Labs and generate a URL.
    uri: str


@pydantic_dataclasses.dataclass
class Message:
    """A Message represents a single message sent  a Llama Labs agents."""

    # The text of the message.
    text: str

    # A mapping of embed keys to Embed objects.
    embeds: dict[str, Embed] = dataclasses.field(default_factory=dict)


@pydantic_dataclasses.dataclass
class AgentQuery:
    """A standalone query sent to a Llama Labs agents."""

    # The contents of the query.
    message: Message

    # The ID of the (human) user for whom this query was made. Agents should treat
    # this as an opaque string and not make any assumptions about its format, other
    # than that it uniquely identifies an end user.
    originating_user_id: Optional[str] = None

    # A session ID that can be used by agents to identify a given user's "session"
    # while interacting with the Llama Labs system. Agents should treat this as an
    # opaque string and not make any assumptions about its format, other than that
    # it uniquely identifies a session for a given user.
    session_id: Optional[str] = None


@pydantic_dataclasses.dataclass
class AgentResponse:
    """A response message from an Agent."""

    # The text of the response message.
    message: Message
