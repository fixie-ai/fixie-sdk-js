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

        if not session_id:
            self._session_id = self._create_session()
        else:
            self._session_id = session_id

    @property
    def gqlclient(self) -> Client:
        """Return the underlying GraphQL client used by this FixieClient."""
        return self._gqlclient

    def agents(self) -> Dict[str, Dict[str, str]]:
        """Return metadata about all running Fixie Agents. The keys of the returned
        dictionary are the Agent IDs, and the values are dictionaries containing
        metadata about each Agent."""

        query = gql(
            """
            query getAgents {
                allAgents {
                    agentId
                    name
                    description
                    developer
                    moreInfo
                }
            }
        """
        )
        result = self._gqlclient.execute(query)
        assert "allAgents" in result and isinstance(result["allAgents"], list)
        agents = result["allAgents"]
        return {agent["agentId"]: agent for agent in agents}

    def sessions(self) -> List[str]:
        """Return a list of all session IDs."""

        query = gql(
            """
            query getPlaygrounds {
                allPlaygrounds {
                    handle
                }
            }
        """
        )
        result = self._gqlclient.execute(query)
        assert "allPlaygrounds" in result and isinstance(result["allPlaygrounds"], list)
        playgrounds = result["allPlaygrounds"]
        return [playground["handle"] for playground in playgrounds]

    @property
    def session_id(self) -> str:
        return self._session_id

    def _create_session(self) -> str:
        query = gql(
            """
            mutation CreatePlayground {
                createPlayground(playgroundData: {}) {
                    playground {
                        handle
                    }
                }
            }
            """
        )
        result = self._gqlclient.execute(query)
        if "createPlayground" not in result or result["createPlayground"] is None:
            raise ValueError(f"Failed to create Session")
        assert isinstance(result["createPlayground"], dict)
        assert isinstance(result["createPlayground"]["playground"], dict)
        assert isinstance(result["createPlayground"]["playground"]["handle"], str)
        return result["createPlayground"]["playground"]["handle"]

    def delete_session(self) -> None:
        query = gql(
            """
            mutation DeletePlayground($handle: String!) {
                deletePlayground(handle: $handle) {
                    playground {
                        handle
                    }
                }
            }
        """
        )
        _ = self._gqlclient.execute(query, variable_values={"handle": self._session_id})

    def get_embeds(self) -> List[Dict[str, Any]]:
        query = gql(
            """
            query getEmbeds($handle: String!) {
                playgroundByHandle(handle: $handle) {
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
            "playgroundByHandle" in result
            and isinstance(result["playgroundByHandle"], dict)
            and isinstance(result["playgroundByHandle"]["embeds"], list)
        )
        return result["playgroundByHandle"]["embeds"]

    def get_messages(self) -> List[Dict[str, Any]]:
        query = gql(
            """
            query getMessages($handle: String!) {
                playgroundByHandle(handle: $handle) {
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
            "playgroundByHandle" in result
            and isinstance(result["playgroundByHandle"], dict)
            and isinstance(result["playgroundByHandle"]["messages"], list)
        )
        return result["playgroundByHandle"]["messages"]

    def query(self, text: str) -> str:
        query = gql(
            """
            mutation Post($handle: String!, $text: String!) {
                addPlaygroundMessage(messageData: {playground: $handle, text: $text}) {
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
