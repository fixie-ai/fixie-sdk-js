import pytest

from fixieai import constants
from fixieai.client.client import FixieClient


@pytest.fixture
def fixie_client():
    return FixieClient(api_key="test-key")


def test_get_agents(fixie_client, requests_mock):
    requests_mock.post(
        constants.FIXIE_GRAPHQL_URL,
        json={
            "data": {"allAgents": [{"agentId": "testuser/test", "name": "Test Agent"}]}
        },
    )
    assert fixie_client.get_agents() == {
        "testuser/test": {"agentId": "testuser/test", "name": "Test Agent"}
    }


def test_get_agent(fixie_client, requests_mock):
    requests_mock.post(
        constants.FIXIE_GRAPHQL_URL,
        json={
            "data": {
                "agentById": {
                    "agentId": "testuser/test-agent-handle",
                    "handle": "test-agent-handle",
                    "name": "Test Agent",
                    "description": "Test Agent Description",
                    "queries": ["test-query"],
                    "moreInfoUrl": "https://test.com",
                    "published": True,
                    "owner": {
                        "username": "testuser",
                    },
                }
            }
        },
    )
    agent = fixie_client.get_agent("testuser/test-agent-handle")
    assert agent.valid
    assert agent.handle == "test-agent-handle"
    assert agent.agent_id == "testuser/test-agent-handle"
    assert agent.name == "Test Agent"
    assert agent.description == "Test Agent Description"
    assert agent.queries == ["test-query"]
    assert agent.more_info_url == "https://test.com"
    assert agent.published is True
    assert agent.owner == "testuser"


def test_create_agent(fixie_client, requests_mock):
    requests_mock.post(
        constants.FIXIE_GRAPHQL_URL,
        json={
            "data": {},
            "errors": ["GraphQL error: No such agent: testuser/test-agent-handle"],
        },
    )
    agent = fixie_client.get_agent("testuser/test-agent-handle")
    assert agent.handle == "test-agent-handle"
    assert agent.agent_id == "testuser/test-agent-handle"
    assert not agent.valid

    # There are two GraphQL calls resulting from create_agent, we need
    # to mock both of the responses.
    requests_mock.post(
        constants.FIXIE_GRAPHQL_URL,
        [
            {
                "json": {
                    "data": {
                        "createAgent": {
                            "agent": {
                                "agentId": "testuser/test-agent-handle",
                            }
                        }
                    }
                },
            },
            {
                "json": {
                    "data": {
                        "agentById": {
                            "agentId": "testuser/test-agent-handle",
                            "handle": "test-agent-handle",
                            "name": "Test Agent",
                            "description": "Test Agent Description",
                            "queries": [],
                            "moreInfoUrl": "https://test.com",
                            "published": True,
                            "owner": {
                                "username": "testuser",
                            },
                        }
                    }
                },
            },
        ],
    )
    agent.create_agent(
        name="Test Agent",
        description="Test Agent Description",
        more_info_url="https://test.com",
        published=True,
    )
    assert agent.valid
    assert agent.agent_id == "testuser/test-agent-handle"
    assert agent.name == "Test Agent"
    assert agent.description == "Test Agent Description"
    assert agent.queries == []
    assert agent.more_info_url == "https://test.com"
    assert agent.published is True
    assert agent.owner == "testuser"


def test_sessions(fixie_client, requests_mock):
    requests_mock.post(
        constants.FIXIE_GRAPHQL_URL,
        json={
            "data": {"allSessions": [{"handle": "test-handle", "name": "Test Session"}]}
        },
    )
    assert fixie_client.get_sessions() == ["test-handle"]


def test_get_session(fixie_client, requests_mock):
    requests_mock.post(
        constants.FIXIE_GRAPHQL_URL,
        json={
            "data": {
                "sessionByHandle": {"handle": "test-handle", "frontendAgentId": None}
            }
        },
    )
    session = fixie_client.get_session("test-handle")

    requests_mock.post(
        constants.FIXIE_GRAPHQL_URL,
        json={
            "data": {
                "sessionByHandle": {
                    "handle": "test-handle",
                    "messages": [
                        {
                            "id": 1,
                            "text": "Test message",
                        }
                    ],
                }
            }
        },
    )
    assert session.get_messages() == [{"id": 1, "text": "Test message"}]
