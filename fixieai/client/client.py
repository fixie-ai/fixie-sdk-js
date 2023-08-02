#!/usr/bin/env python3

from __future__ import annotations

import enum
import logging
from typing import Any, BinaryIO, Dict, List, Optional

import requests
from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport

from fixieai import constants
from fixieai.client import utils
from fixieai.client.agent import Agent
from fixieai.client.session import Session


class FixieEnvironment(str, enum.Enum):
    PYTHON = "PYTHON"
    NODEJS = "NODEJS"


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
        api_key: The API key for the Fixie API server. If not provided, the
            FIXIE_API_KEY environment variable will be used. If that is not
            set, the authenticated user API key will be used, or a ValueError
            will be raised if the user is not authenticated.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        self._api_key = api_key or constants.fixie_api_key()
        logging.info(f"Using Fixie API URL: {constants.FIXIE_API_URL}")
        self._request_headers = {"Authorization": f"Bearer {self._api_key}"}
        transport = RequestsHTTPTransport(
            url=constants.FIXIE_GRAPHQL_URL,
            headers=self._request_headers,
        )
        self._gqlclient = Client(transport=transport, fetch_schema_from_transport=False)

    @property
    def gqlclient(self) -> Client:
        """Return the underlying GraphQL client used by this FixieClient."""
        return self._gqlclient

    @property
    def url(self) -> str:
        """Return the URL of the Fixie API server."""
        return constants.FIXIE_API_URL

    def clone(self) -> "FixieClient":
        """Return a new FixieClient instance with the same configuration."""
        return FixieClient(api_key=self._api_key)

    def get_agents(self) -> Dict[str, Dict[str, str]]:
        """Return metadata about all running Fixie Agents. The keys of the returned
        dictionary are the Agent handles, and the values are dictionaries containing
        metadata about each Agent."""

        query = gql(
            """
            query getAgents {
                allAgents {
                    agentId
                    name
                    description
                    moreInfoUrl
                }
            }
        """
        )
        result = self._gqlclient.execute(query)
        assert "allAgents" in result and isinstance(result["allAgents"], list)
        agents = result["allAgents"]
        return {agent["agentId"]: agent for agent in agents}

    def get_agent(self, agent_id: str) -> Agent:
        """Return an existing Agent object."""
        return Agent(self, agent_id)

    def get_agent_page_url(self, agent_id: str) -> str:
        """Return the URL of the Agent page on the Fixie Platform."""
        return f"{constants.FIXIE_AGENT_URL}/{agent_id}"

    def create_agent(
        self,
        handle: str,
        name: str,
        description: str,
        query_url: Optional[str] = None,
        func_url: Optional[str] = None,
        more_info_url: Optional[str] = None,
        published: Optional[bool] = None,
    ) -> Agent:
        """Create a new Agent.

        Args:
            handle: The handle for the new Agent. This must be unique across all
                Agents owned by this user.
            name: The name of the new Agent.
            description: A description of the new Agent.
            query_url: (deprecated) Unused.
            func_url: (deprecated) The URL of the new Agent's func endpoint.
            more_info_url: A URL with more information about the new Agent.
            published: Whether the new Agent should be published.
        """
        agent = Agent(self, f"{self.get_current_username()}/{handle}")
        agent.create_agent(
            name, description, query_url, func_url, more_info_url, published
        )
        return agent

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

    def create_session(self, frontend_agent_id: Optional[str] = None) -> Session:
        """Create a new Session."""
        return Session(self, frontend_agent_id=frontend_agent_id)

    def get_session(self, session_id: str) -> Session:
        """Return an existing Session object."""
        return Session(self, session_id)

    def get_current_user(self) -> Dict[str, Any]:
        """Returns the user metadata of the current user."""
        query = gql(
            """
            query getUsername {
                user {
                    username
                    firstName
                    lastName
                    email
                    organization {
                        handle
                        name
                    }
                    dailyQueryLimit
                    dailyUsedQueries
                    avatar
                }
            }
        """
        )
        result = self._gqlclient.execute(query)
        assert "user" in result and isinstance(result["user"], dict)
        return result["user"]

    def get_current_username(self) -> str:
        """Returns the username of the current user."""
        user = self.get_current_user()
        assert "username" in user and isinstance(user["username"], str)
        return user["username"]

    def refresh_agent(self, agent_handle: str):
        """Indicates that an agent's prompts should be refreshed."""
        username = self.get_current_username()
        requests.post(
            f"{constants.FIXIE_REFRESH_URL}/{username}/{agent_handle}",
            headers=self._request_headers,
        ).raise_for_status()

    def create_agent_revision(
        self,
        handle: str,
        make_current: bool,
        *,
        reindex_corpora: bool = False,
        metadata: Optional[Dict[str, str]] = None,
        external_url: Optional[str] = None,
        gzip_tarfile: Optional[BinaryIO] = None,
        environment: FixieEnvironment = FixieEnvironment.PYTHON,
    ) -> str:
        """Creates a new Agent revision.

        Args:
            handle: The handle of the Agent. Must be owned by the current user.
            make_current: Whether the new revision should be made the current (active) revision.
            reindex_corpora: Whether to reindex all corpora for the new revision.
            metadata: Optional client-provided metadata to associate with the revision.
            external_url: The URL at which the revision is hosted, if hosted externally.
            gzip_tarfile: A file-like of a gzip-compressed tarfile containing the files to deploy.
            environment: The environment in which the revision should be run.

        Exactly one of `external_url` and `gzip_tarfile` must be provided.
        """

        mutation = gql(
            """
            mutation CreateAgentRevision(
                $handle: String!,
                $metadata: [RevisionMetadataKeyValuePairInput!]!,
                $makeCurrent: Boolean!,
                $externalDeployment: ExternalDeploymentInput,
                $managedDeployment: ManagedDeploymentInput,
                $reindexCorpora: Boolean!,
            ) {
                createAgentRevision(agentHandle: $handle, makeCurrent: $makeCurrent, revision: { 
                    metadata: $metadata
                    externalDeployment: $externalDeployment
                    managedDeployment: $managedDeployment
                }, reindexCorpora: $reindexCorpora) {
                    revision {
                        id
                    }
                }
            }
            """
        )

        with utils.patched_gql_file_uploader(
            gzip_tarfile, "upload.tar.gz", "application/gzip"
        ):
            result = self._gqlclient.execute(
                mutation,
                variable_values={
                    "handle": handle,
                    "metadata": [
                        {"key": key, "value": value} for key, value in metadata.items()
                    ]
                    if metadata
                    else [],
                    "makeCurrent": make_current,
                    "reindexCorpora": reindex_corpora,
                    "externalDeployment": {"url": external_url}
                    if external_url
                    else None,
                    "managedDeployment": {
                        "environment": environment,
                        "codePackage": gzip_tarfile,
                    }
                    if gzip_tarfile
                    else None,
                },
                upload_files=True,
            )

        revision_id = result["createAgentRevision"]["revision"]["id"]
        assert isinstance(revision_id, str)
        return revision_id

    def get_current_agent_revision(self, handle: str) -> Optional[str]:
        """Gets the current (active) revision of an agent."""
        agent = self.get_agent(handle)
        query = gql(
            """
            query GetRevisionId($agentId: String!) {
                agentById(agentId: $agentId) {
                    currentRevision {
                        id
                    }
                }
            }
            """
        )

        response = self._gqlclient.execute(
            query,
            variable_values={"agentId": agent.agent_id},
        )

        revision = response["agentById"]["currentRevision"]
        return revision["id"] if revision is not None else None

    def set_current_agent_revision(self, handle: str, revision_id: str):
        """Sets the current (active) revision of an agent."""

        mutation = gql(
            """
            mutation SetCurrentAgentRevision(
                $handle: String!,
                $currentRevisionId: ID!) {
                updateAgent(
                    agentData: {
                        handle: $handle,
                        currentRevisionId: $currentRevisionId
                    }
                ) {
                    agent {
                        agentId
                    }
                }
            }
            """
        )

        _ = self._gqlclient.execute(
            mutation,
            variable_values={"handle": handle, "currentRevisionId": revision_id},
        )

    def delete_agent_revision(self, handle: str, revision_id: str):
        """Deletes an Agent revision."""

        mutation = gql(
            """
            mutation DeleteRevision($handle: String!, $revisionId: ID!) {
                deleteAgentRevision(agentHandle: $handle, revisionId: $revisionId) {
                    agent {
                        agentId
                    }
                }
            }
            """
        )
        _ = self._gqlclient.execute(
            mutation, variable_values={"handle": handle, "revisionId": revision_id}
        )

    def deploy_agent(
        self, handle: str, gzip_tarfile: BinaryIO, environment: FixieEnvironment
    ):
        """Deploys an agent implementation.

        Args:
            handle: The handle of the Agent to deploy. Must be owned by the current user.
            gzip_tarfile: A file-like of a gzip-compressed tarfile containing the files to deploy.
        """
        return self.create_agent_revision(
            handle,
            make_current=True,
            gzip_tarfile=gzip_tarfile,
            environment=environment,
        )
