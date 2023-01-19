#!/usr/bin/env python3

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport

from llamalabs.session import Session

_CLIENT: Optional["LlamaLabsClient"] = None
_SESSION: Optional[Session] = None


def client() -> LlamaLabsClient:
    """Return the global LlamaLabsClient instance."""
    global _CLIENT
    if not _CLIENT:
        _CLIENT = LlamaLabsClient()
    assert _CLIENT is not None
    return _CLIENT


def session() -> Session:
    """Return the global Llama Labs Session instance."""
    global _SESSION
    if not _SESSION:
        _SESSION = Session(client())
    assert _SESSION is not None
    return _SESSION


def agents() -> Dict[str, Dict[str, str]]:
    """Return metadata about all Llama Labs Agents. The keys of the returned
    dictionary are Agent IDs, and the values are dictionaries containing
    metadata about each Agent."""
    return client().get_agents()


def query(text: str) -> str:
    """Return metadata about all Llama Labs Agents. The keys of the returned
    dictionary are Agent IDs, and the values are dictionaries containing
    metadata about each Agent."""
    return session().query(text)


def embeds() -> List[Dict[str, Any]]:
    """Return metadata about all Llama Labs Agents. The keys of the returned
    dictionary are Agent IDs, and the values are dictionaries containing
    metadata about each Agent."""
    return session().get_embeds()


class LlamaLabsClient:
    """LlamaLabsClient is a client to the Llama Labs system.

    Args:
        api_url: The URL of the Llama Labs API server. If not provided, the
            FIXIE_API_URL environment variable will be used. If that is not
            set, the default value of "https://app.fixie.ai" will be used.
        api_key: The API key for the Llama Labs API server. If not provided, the
            FIXIE_API_KEY environment variable will be used. If that is not
            set, a ValueError will be raised.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self._api_url = api_url or os.getenv("FIXIE_API_URL", "https://app.fixie.ai")
        self._api_key = api_key or os.getenv("FIXIE_API_KEY")
        if not self._api_key:
            raise ValueError(
                "No Llama Labs API key provided. Set the FIXIE_API_KEY environment variable "
                "to your API key, which can be obtained from your profile page on "
                "https://app.fixie.ai."
            )
        transport = RequestsHTTPTransport(
            url=f"{self._api_url}/graphql",
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        self._gqlclient = Client(transport=transport, fetch_schema_from_transport=False)

    @property
    def gqlclient(self) -> Client:
        """Return the underlying GraphQL client used by this LlamaLabsClient."""
        return self._gqlclient

    @property
    def url(self) -> str:
        """Return the URL of the Llama Labs API server."""
        assert self._api_url is not None
        return self._api_url

    def clone(self) -> "LlamaLabsClient":
        """Return a new LlamaLabsClient instance with the same configuration."""
        return LlamaLabsClient(api_url=self._api_url, api_key=self._api_key)

    def get_agents(self) -> Dict[str, Dict[str, str]]:
        """Return metadata about all running Llama Labs Agents. The keys of the returned
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

    def get_sessions(self) -> List[str]:
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

    def create_session(self) -> Session:
        """Create a new Session."""
        return Session(self)

    def get_session(self, session_id: str) -> Session:
        """Return an existing Session object."""
        return Session(self, session_id)
