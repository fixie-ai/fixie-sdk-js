#!/usr/bin/env python3

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport

from fixieai import constants
from fixieai.client.session import Session

_CLIENT: Optional["FixieClient"] = None
_SESSION: Optional[Session] = None


def get_client() -> FixieClient:
    """Return the global FixieClient instance."""
    global _CLIENT
    if not _CLIENT:
        _CLIENT = FixieClient()
    assert _CLIENT is not None
    return _CLIENT


def get_session() -> Session:
    """Return the global Fixie Session instance."""
    global _SESSION
    if not _SESSION:
        _SESSION = Session(get_client())
    assert _SESSION is not None
    return _SESSION


def get_agents() -> Dict[str, Dict[str, str]]:
    """Return metadata about all Fixie Agents. The keys of the returned
    dictionary are Agent IDs, and the values are dictionaries containing
    metadata about each Agent."""
    return get_client().get_agents()


def query(text: str) -> str:
    """Run a query."""
    return get_session().query(text)


def get_embeds() -> List[Dict[str, Any]]:
    """Return a list of Embeds."""
    return get_session().get_embeds()


class FixieClient:
    """FixieClient is a client to the Fixie system.

    Args:
        api_url: The URL of the Fixie API server. If not provided, the
            FIXIE_API_URL environment variable will be used. If that is not
            set, the default value of "https://app.fixie.ai " will be used.
        api_key: The API key for the Fixie API server. If not provided, the
            FIXIE_API_KEY environment variable will be used. If that is not
            set, a ValueError will be raised.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self._api_url = api_url or constants.FIXIE_API_URL
        self._api_key = api_key or constants.FIXIE_API_KEY
        if not self._api_key:
            raise ValueError(
                "No Fixie API key provided. Set the FIXIE_API_KEY environment variable "
                "to your API key, which can be obtained from your profile page on "
                "https://app.fixie.ai "
            )
        logging.info(f"Using Fixie API URL: {self._api_url}")
        transport = RequestsHTTPTransport(
            url=f"{self._api_url}/graphql",
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        self._gqlclient = Client(transport=transport, fetch_schema_from_transport=False)

    @property
    def gqlclient(self) -> Client:
        """Return the underlying GraphQL client used by this FixieClient."""
        return self._gqlclient

    @property
    def url(self) -> str:
        """Return the URL of the Fixie API server."""
        assert self._api_url is not None
        return self._api_url

    def clone(self) -> "FixieClient":
        """Return a new FixieClient instance with the same configuration."""
        return FixieClient(api_url=self._api_url, api_key=self._api_key)

    def get_agents(self) -> Dict[str, Dict[str, str]]:
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
