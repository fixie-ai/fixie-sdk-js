#!/usr/bin/env python3

import os
from typing import Dict, List, Optional

from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport

from fixie.playground import Playground


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

    def playgrounds(self) -> List[Playground]:
        """Return a list of all Fixie Playgrounds."""

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
        return [Playground(self, playground["handle"]) for playground in playgrounds]


    def get_playground(self, handle: str) -> Playground:
        return Playground(self, handle)


