import pytest
import requests_mock

from fixieai.client.client import FixieClient


@pytest.fixture
def fixie_client():
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.fixie.ai/graphql",
            json={"data": {"createSession": {"session": {"handle": "test-handle"}}}},
        )
        return FixieClient(api_url="https://test.fixie.ai", api_key="test-key")


def test_get_agents(fixie_client):
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.fixie.ai/graphql",
            json={"data": {"allAgents": [{"handle": "test", "name": "Test Agent"}]}},
        )
        assert fixie_client.get_agents() == {
            "test": {"handle": "test", "name": "Test Agent"}
        }


def test_get_agent(fixie_client):
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.fixie.ai/graphql",
            json={
                "data": {
                    "agentByHandle": {
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
        client = FixieClient(
            api_url="https://test.fixie.ai",
            api_key="test-key",
        )
        agent = client.get_agent("test-agent-handle")
        assert agent.handle == "test-agent-handle"
        assert agent.agent_id == "testuser/test-agent-handle"
        assert agent.name == "Test Agent"
        assert agent.description == "Test Agent Description"
        assert agent.queries == ["test-query"]
        assert agent.more_info_url == "https://test.com"
        assert agent.published is True
        assert agent.owner == "testuser"


def test_create_agent(fixie_client):
    with requests_mock.Mocker() as m:
        client = FixieClient(
            api_url="https://test.fixie.ai",
            api_key="test-key",
        )

        m.post(
            "https://test.fixie.ai/graphql",
            json={
                "data": {},
                "errors": ["GraphQL error: No such agent: testuser/test-agent-handle"],
            },
        )
        agent = client.get_agent("test-agent-handle")
        assert agent.handle == "test-agent-handle"
        assert agent.agent_id is None

        # There are two GraphQL calls resulting from create_agent, we need
        # to mock both of the responses.
        m.post(
            "https://test.fixie.ai/graphql",
            [
                {
                    "json": {
                        "data": {
                            "createAgent": {
                                "agent": {
                                    "agentId": "testuser/test-agent-id",
                                }
                            }
                        }
                    },
                },
                {
                    "json": {
                        "data": {
                            "agentByHandle": {
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
        assert agent.agent_id == "testuser/test-agent-handle"
        assert agent.name == "Test Agent"
        assert agent.description == "Test Agent Description"
        assert agent.queries == []
        assert agent.more_info_url == "https://test.com"
        assert agent.published is True
        assert agent.owner == "testuser"


def test_sessions(fixie_client):
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.fixie.ai/graphql",
            json={
                "data": {
                    "allSessions": [{"handle": "test-handle", "name": "Test Session"}]
                }
            },
        )
        assert fixie_client.get_sessions() == ["test-handle"]


def test_get_session():
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.fixie.ai/graphql",
            json={
                "data": {
                    "sessionByHandle": {
                        "handle": "test-handle",
                    }
                }
            },
        )
        client = FixieClient(
            api_url="https://test.fixie.ai",
            api_key="test-key",
        )
        session = client.get_session("test-handle")

        m.post(
            "https://test.fixie.ai/graphql",
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
