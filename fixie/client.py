#!/usr/bin/env python3

import os
from typing import Any, Dict, List, Optional

from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport

_CLIENT: Optional["FixieClient"] = None


def client() -> "FixieClient":
    """Return the global FixieClient instance."""
    global _CLIENT
    if not _CLIENT:
        _CLIENT = FixieClient()
    assert _CLIENT is not None
    return _CLIENT


def agents() -> Dict[str, Dict[str, str]]:
    """Return metadata about all Fixie Agents. The keys of the returned
    dictionary are Agent IDs, and the values are dictionaries containing
    metadata about each Agent."""
    return client().agents()


def query(text: str) -> str:
    """Return metadata about all Fixie Agents. The keys of the returned
    dictionary are Agent IDs, and the values are dictionaries containing
    metadata about each Agent."""
    return client().query(text)


def embeds() -> List[Dict[str, Any]]:
    """Return metadata about all Fixie Agents. The keys of the returned
    dictionary are Agent IDs, and the values are dictionaries containing
    metadata about each Agent."""
    return client().get_embeds()


class FixieClient:
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self._api_url = api_url or os.getenv("FIXIE_API_URL", "https://app.fixie.ai")
        self._api_key = api_key or os.getenv("FIXIE_API_KEY")
        if not self._api_key:
            raise ValueError(
                "No Fixie API key provided. Set the FIXIE_API_KEY environment variable "
                "to your API key, which can be obtained from your profile page on "
                "https://app.fixie.ai."
            )
        transport = RequestsHTTPTransport(
            url=f"{self._api_url}/graphql",
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        self._gqlclient = Client(transport=transport, fetch_schema_from_transport=False)
        self._session_id = session_id

    @property
    def gqlclient(self) -> Client:
        """Return the underlying GraphQL client used by this FixieClient."""
        return self._gqlclient

    def agents(self) -> Dict[str, Dict[str, str]]:
        """Return metadata about all running Fixie Agents. The keys of the returned
        dictionary are the Agent handles, and the values are dictionaries containing
        metadata about each Agent."""

        query = gql(
            """
            query getAgents {
                allAgents {
                    handle
                    name
                    description
                }
            }
        """
        )
        result = self._gqlclient.execute(query)
        assert "allAgents" in result and isinstance(result["allAgents"], list)
        agents = result["allAgents"]
        return {agent["handle"]: agent for agent in agents}

    def sessions(self) -> List[str]:
        """Return a list of all session IDs."""

        query = gql(
            """
            query getSessions {
                allSessions {
                    handle
                }
            }
        """
        )
        result = self._gqlclient.execute(query)
        assert "allSessions" in result and isinstance(result["allSessions"], list)
        sessions = result["allSessions"]
        return [session["handle"] for session in sessions]

    @property
    def session_id(self) -> Optional[str]:
        self._ensure_session()
        return self._session_id

    def _ensure_session(self):
        """Create a new session if one does not already exist."""
        if self._session_id:
            return

        query = gql(
            """
            mutation CreateSession {
                createSession(sessionData: {}) {
                    session {
                        handle
                    }
                }
            }
            """
        )
        result = self._gqlclient.execute(query)
        if "createSession" not in result or result["createSession"] is None:
            raise ValueError(f"Failed to create Session")
        assert isinstance(result["createSession"], dict)
        assert isinstance(result["createSession"]["session"], dict)
        assert isinstance(result["createSession"]["session"]["handle"], str)
        self._session_id = result["createSession"]["session"]["handle"]

    def delete_session(self) -> None:
        self._ensure_session()
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
        self._ensure_session()
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
                                id
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
        self._ensure_session()
        query = gql(
            """
            query getMessages($handle: String!) {
                sessionByHandle(handle: $handle) {
                    messages {
                        id
                        text
                        sentBy
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

    def query(self, text: str) -> str:
        query = gql(
            """
            mutation Post($handle: String!, $text: String!) {
                addSessionMessage(messageData: {session: $handle, text: $text}) {
                    message {
                        text
                    }
                }
            }
            """
        )
        result = self._gqlclient.execute(
            query, variable_values={"handle": self._session_id, "text": text}
        )

        # The reply to the query comes in as the most recent 'response' message in the session.
        response = self.get_messages()[-1]
        assert isinstance(response["text"], str)
        return response["text"]
