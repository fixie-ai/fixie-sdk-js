#!/usr/bin/env python3

import os
from typing import List, Optional

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

FIXIE_API_HOST = os.getenv("FIXIE_API_HOST", "app.fixie.ai")
FIXIE_API_KEY = os.getenv("FIXIE_API_KEY")


class FixieClient:
    def __init__(self, api_host: str = FIXIE_API_HOST, api_key: Optional[str] = None):
        self._api_host = api_host
        self._api_key = api_key or os.getenv("FIXIE_API_KEY")
        if not self._api_key:
            raise ValueError(
                "No Fixie API key provided. Set the FIXIE_API_KEY environment variable "
                "to your API key, which can be obtained from your profile page on "
                "https://app.fixie.ai."
            )
        transport = RequestsHTTPTransport(
            url=f"https://{self._api_host}/graphql",
            headers={"x-api-key": self._api_key},
        )
        self._gqlclient = Client(transport=transport, fetch_schema_from_transport=True)

    def agents(self) -> List[str]:
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
        print(result)
        return []


if __name__ == "__main__":
    client = FixieClient()
    print(client.agents())
