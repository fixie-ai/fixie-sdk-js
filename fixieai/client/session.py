#!/usr/bin/env python3

from __future__ import annotations

from fixieai import constants
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional

from gql import gql

if TYPE_CHECKING:
    import fixieai.client as fixie_client

    FixieClient = fixie_client.FixieClient
else:
    FixieClient = Any


class Session:
    """Represents a single session with the Fixie system.

    Args:
        client: The FixieClient instance to use.
        session_id: The ID of the session to use. If not provided, a new
            session will be created.
    """

    def __init__(
        self,
        client: FixieClient,
        session_id: Optional[str] = None,
        frontend_agent_id: Optional[str] = None,
    ):
        self._client = client
        self._gqlclient = self._client.gqlclient
        self._session_id = session_id
        self._frontend_agent_id = frontend_agent_id
        if session_id:
            # Test that the session exists.
            _ = self.get_metadata()
            assert (
                frontend_agent_id is None
            ), "Cannot specify frontend_agent_id when using an existing session"
        else:
            self._session_id = self._create_session(frontend_agent_id)

    @property
    def session_id(self) -> Optional[str]:
        """Return the session ID used by this Fixie client."""
        return self._session_id

    @property
    def session_url(self) -> str:
        """Return the URL of the Fixie session."""
        return f"{self._client.url}/sessions/{self.session_id}"

    @property
    def frontend_agent_id(self) -> Optional[str]:
        """Return the frontend agent ID used by this Fixie client."""
        return self._frontend_agent_id

    def _create_session(self, frontend_agent_id: Optional[str] = None) -> str:
        """Create a new session."""
        assert self._session_id is None

        query = gql(
            """
            mutation CreateSession($frontendAgentId: String) {
                createSession(sessionData: {frontendAgentId: $frontendAgentId}) {
                    session {
                        handle
                        frontendAgentId
                    }
                }
            }
            """
        )

        result = self._gqlclient.execute(
            query, variable_values={"frontendAgentId": frontend_agent_id}
        )
        if "createSession" not in result or result["createSession"] is None:
            raise ValueError(f"Failed to create Session")
        assert isinstance(result["createSession"], dict)
        assert isinstance(result["createSession"]["session"], dict)
        assert isinstance(result["createSession"]["session"]["handle"], str)
        return result["createSession"]["session"]["handle"]

    def get_metadata(self) -> Dict[str, Any]:
        """Return metadata about this session."""

        query = gql(
            """
            query getSession($session_id: String!) {
                sessionByHandle(handle: $session_id) {
                    handle
                    name
                    description
                    frontendAgentId
                }
            }
        """
        )
        result = self._gqlclient.execute(
            query, variable_values={"session_id": self._session_id}
        )
        assert "sessionByHandle" in result and isinstance(
            result["sessionByHandle"], dict
        )
        self._frontend_agent_id = result["sessionByHandle"]["frontendAgentId"]
        return result["sessionByHandle"]

    def delete_session(self) -> None:
        """Delete the current session."""
        query = gql(
            """
            mutation DeleteSession($handle: String!) {
                deleteSession(handle: $handle) {
                    session {
                        handle
                    }
                }
            }
        """
        )
        _ = self._gqlclient.execute(query, variable_values={"handle": self._session_id})

    def get_embeds(self) -> List[Dict[str, Any]]:
        """Return the Embeds attached to this Session."""
        query = gql(
            """
            query getEmbeds($handle: String!) {
                sessionByHandle(handle: $handle) {
                    embeds {
                        key
                        embed {
                            id
                            contentType
                            created
                            contentHash
                            owner {
                                username
                            }
                            url
                        }
                    }
                }
            }
        """
        )
        result = self._gqlclient.execute(
            query, variable_values={"handle": self._session_id}
        )
        assert (
            "sessionByHandle" in result
            and isinstance(result["sessionByHandle"], dict)
            and isinstance(result["sessionByHandle"]["embeds"], list)
        )
        return result["sessionByHandle"]["embeds"]

    def get_messages(self) -> List[Dict[str, Any]]:
        """Return the messages that make up this session."""
        query = gql(
            """
            query getMessages($handle: String!) {
                sessionByHandle(handle: $handle) {
                    messages {
                        id
                        text
                        sentBy {
                            handle
                        }
                        type
                        inReplyTo { id }
                        timestamp
                    }
                }
            }
        """
        )
        result = self._gqlclient.execute(
            query, variable_values={"handle": self._session_id}
        )
        assert (
            "sessionByHandle" in result
            and isinstance(result["sessionByHandle"], dict)
            and isinstance(result["sessionByHandle"]["messages"], list)
        )
        return result["sessionByHandle"]["messages"]

    def query(self, text: str):
        """Run a single query against the Fixie API and return the response."""
        final = None
        for message in self.streaming_query(text):
            final = message
        return final

    def streaming_query(self, text: str) -> Generator[Dict[str, Any], None, None]:
        """Run a single query against the Fixie API and return a stream."""
        data = {
            "session": self._session_id,
            "message": {"text": text},
            "stream": True,
        }
        url = f"{constants.FIXIE_AGENT_URL}/{self._frontend_agent_id}"
        gen = self._client.streaming_post(url, data)
        return (response["message"] for response in gen)
