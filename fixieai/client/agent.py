from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from gql import gql

if TYPE_CHECKING:
    import fixieai.client as fixie_client

    FixieClient = fixie_client.FixieClient
else:
    FixieClient = Any


class Agent:
    """Provides an interface to the Fixie GraphQL Agent API.

    Args:
        client: The FixieClient instance to use.
        handle: The handle of the Agent.
    """

    def __init__(
        self,
        client: FixieClient,
        handle: str,
    ):
        self._client = client
        self._gqlclient = self._client.gqlclient
        self._handle = handle
        self._metadata: Optional[Dict[str, Any]] = None
        try:
            self._metadata = self.get_metadata()
        except:
            self._metadata = None

    @property
    def handle(self) -> Optional[str]:
        """Return the handle for this Agent."""
        return self._handle

    @property
    def agent_id(self) -> Optional[str]:
        """Return the agentId for this Agent."""
        if self._metadata is None:
            return None
        agent_id = self._metadata["agentId"]
        assert isinstance(agent_id, str)
        return agent_id

    @property
    def name(self) -> Optional[str]:
        """Return the name for this Agent."""
        if self._metadata is None:
            return None
        name = self._metadata["name"]
        assert isinstance(name, str)
        return name

    @property
    def description(self) -> Optional[str]:
        """Return the description for this Agent."""
        if self._metadata is None:
            return None
        description = self._metadata["description"]
        assert isinstance(description, str)
        return description

    @property
    def queries(self) -> Optional[List[str]]:
        """Return the queries for this Agent."""
        if self._metadata is None:
            return None
        queries = self._metadata["queries"]
        assert isinstance(queries, list) and all(isinstance(q, str) for q in queries)
        return queries

    @property
    def more_info_url(self) -> Optional[str]:
        """Return the more info URL for this Agent."""
        if self._metadata is None:
            return None
        more_info_url = self._metadata["moreInfoUrl"]
        assert isinstance(more_info_url, str)
        return more_info_url

    @property
    def published(self) -> Optional[bool]:
        """Return the published status for this Agent."""
        if self._metadata is None:
            return None
        published = self._metadata["published"]
        assert isinstance(published, bool)
        return published

    @property
    def owner(self) -> Optional[str]:
        """Return the owner of this Agent."""
        if self._metadata is None:
            return None
        owner_username = self._metadata["owner"]["username"]
        assert isinstance(owner_username, str)
        return owner_username

    @property
    def query_url(self) -> Optional[str]:
        """Return the query URL for this Agent."""
        if self._metadata is None:
            return None
        url = self._metadata["owner"]["query_url"]
        assert isinstance(url, str)
        return url

    @property
    def func_url(self) -> Optional[str]:
        """Return the func URL for this Agent."""
        if self._metadata is None:
            return None
        url = self._metadata["owner"]["func_url"]
        assert isinstance(url, str)
        return url

    @property
    def created(self) -> Optional[datetime.datetime]:
        """Return the creation timestamp for this Agent."""
        if self._metadata is None:
            return None
        ts = self._metadata["owner"]["created"]
        assert isinstance(ts, datetime.datetime)
        return ts

    @property
    def modified(self) -> Optional[datetime.datetime]:
        """Return the modification timestamp for this Agent."""
        if self._metadata is None:
            return None
        ts = self._metadata["owner"]["modified"]
        assert isinstance(ts, datetime.datetime)
        return ts

    def get_metadata(self) -> Dict[str, Any]:
        """Return metadata about this Agent."""

        query = gql(
            """
            query getAgentByHandle($handle: String!) {
                agentByHandle(handle: $handle) {
                    agentId
                    handle
                    name
                    description
                    queries
                    moreInfoUrl
                    published
                    owner {
                        username
                    }
                    queryUrl
                    funcUrl
                    created
                    modified
                }
            }
        """
        )
        result = self._gqlclient.execute(
            query, variable_values={"handle": self._handle}
        )
        if "agentByHandle" not in result or result["agentByHandle"] is None:
            raise ValueError(f"Cannot fetch agent metadata for {self._handle}")
        agent_by_handle = result["agentByHandle"]
        assert isinstance(agent_by_handle, dict) and all(
            isinstance(k, str) for k in agent_by_handle.keys()
        )
        return agent_by_handle

    def create_agent(
        self,
        name: str,
        description: str,
        query_url: Optional[str] = None,
        func_url: Optional[str] = None,
        more_info_url: Optional[str] = None,
        published: Optional[bool] = None,
    ) -> str:
        """Create a new Agent with the given parameters."""
        query = gql(
            """
            mutation CreateAgent(
                $handle: String!,
                $name: String!,
                $description: String!,
                $queryUrl: String,
                $funcUrl: String,
                $moreInfoUrl: String,
                $published: Boolean) {
                createAgent(
                    agentData: {
                        handle: $handle,
                        name: $name,
                        description: $description,
                        queryUrl: $queryUrl,
                        funcUrl: $funcUrl,
                        moreInfoUrl: $moreInfoUrl,
                        published: $published
                    }
                ) {
                    agent {
                        agentId
                    }
                }
            }
            """
        )

        variable_values: Dict[str, Any] = {"handle": self._handle}
        variable_values["name"] = name
        variable_values["description"] = description
        if query_url is not None:
            variable_values["query_url"] = query_url
        if func_url is not None:
            variable_values["func_url"] = func_url
        if more_info_url is not None:
            variable_values["moreInfoUrl"] = more_info_url
        if published is not None:
            variable_values["published"] = published

        result = self._gqlclient.execute(query, variable_values=variable_values)
        if "createAgent" not in result or result["createAgent"] is None:
            raise ValueError(f"Failed to create Agent")
        assert isinstance(result["createAgent"], dict)
        assert isinstance(result["createAgent"]["agent"], dict)
        assert isinstance(result["createAgent"]["agent"]["agentId"], str)
        self._metadata = self.get_metadata()
        return result["createAgent"]["agent"]["agentId"]

    def update_agent(
        self,
        new_handle: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        query_url: Optional[str] = None,
        func_url: Optional[str] = None,
        more_info_url: Optional[str] = None,
        published: Optional[bool] = None,
    ) -> str:
        """Update the Agent with the given parameters."""
        query = gql(
            """
            mutation UpdateAgent(
                $handle: String!,
                $newHandle: String,
                $name: String,
                $description: String,
                $queryUrl: String,
                $funcUrl: String,
                $moreInfoUrl: String,
                $published: Boolean) {
                updateAgent(
                    agentData: {
                        handle: $handle,
                        newHandle: $newHandle,
                        name: $name,
                        description: $description,
                        queryUrl: $queryUrl,
                        funcUrl: $funcUrl,
                        moreInfoUrl: $moreInfoUrl,
                        published: $published
                    }
                ) {
                    agent {
                        agentId
                    }
                }
            }
            """
        )

        variable_values: Dict[str, Any] = {"handle": self._handle}
        if new_handle is not None:
            variable_values["newHandle"] = new_handle
        if name is not None:
            variable_values["name"] = name
        if description is not None:
            variable_values["description"] = description
        if query_url is not None:
            variable_values["query_url"] = query_url
        if func_url is not None:
            variable_values["func_url"] = func_url
        if more_info_url is not None:
            variable_values["moreInfoUrl"] = more_info_url
        if published is not None:
            variable_values["published"] = published

        result = self._gqlclient.execute(query, variable_values=variable_values)
        if "updateAgent" not in result or result["updateAgent"] is None:
            raise ValueError(f"Failed to update Agent")
        assert isinstance(result["updateAgent"], dict)
        assert isinstance(result["updateAgent"]["agent"], dict)
        assert isinstance(result["updateAgent"]["agent"]["agentId"], str)
        self._metadata = self.get_metadata()
        if new_handle:
            self._handle = new_handle
        return result["updateAgent"]["agent"]["agentId"]

    def delete_agent(self) -> None:
        """Delete this Agent."""
        query = gql(
            """
            mutation DeleteAgent($handle: String!) {
                deleteAgent(handle: $handle) {
                    agent {
                        handle
                    }
                }
            }
        """
        )
        _ = self._gqlclient.execute(query, variable_values={"handle": self._handle})
