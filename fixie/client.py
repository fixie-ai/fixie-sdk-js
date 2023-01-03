#!/usr/bin/env python3

import os
from typing import Any, Dict, Optional

from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport


class FixieClient:
    def __init__(self, api_host: Optional[str] = None, api_key: Optional[str] = None):
        self._api_host = api_host or os.getenv("FIXIE_API_HOST", "app.fixie.ai")
        self._api_key = api_key or os.getenv("FIXIE_API_KEY")
        if not self._api_key:
            raise ValueError(
                "No Fixie API key provided. Set the FIXIE_API_KEY environment variable "
                "to your API key, which can be obtained from your profile page on "
                "https://app.fixie.ai."
            )
        transport = RequestsHTTPTransport(
            url=f"https://{self._api_host}/graphql",
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        self._gqlclient = Client(transport=transport, fetch_schema_from_transport=False)

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

    def playgrounds(self) -> Dict[str, str]:
        """Return metadata about all Fixie Playgrounds. The keys of the returned
        dictionary are the Playground handles, and the values are dictionaries containing
        metadata about each Playground."""

        query = gql(
            """
            query getPlaygrounds {
                allPlaygrounds {
                    handle
                    name
                    description
                    owner {
                        username
                    }
                }
            }
        """
        )
        result = self._gqlclient.execute(query)
        assert "allPlaygrounds" in result and isinstance(result["allPlaygrounds"], list)
        playgrounds = result["allPlaygrounds"]
        return {playground["handle"]: playground for playground in playgrounds}

    def get_playground(self, handle: str) -> Dict[str, Any]:

        query = gql(
            """
            query getPlayground($handle: String!) {
                playgroundByHandle(handle: $handle) {
                    handle
                    name
                    description
                    owner {
                        username
                    }
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
        result = self._gqlclient.execute(query, variable_values={"handle": handle})
        assert "playgroundByHandle" in result and isinstance(
            result["playgroundByHandle"], dict
        )
        return result["playgroundByHandle"]
