import pytest
import requests_mock

from llamalabs.client import LlamaLabsClient


@pytest.fixture
def llamalabs_client():
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.llamalabs.ai/graphql",
            json={"data": {"createSession": {"session": {"handle": "test-handle"}}}},
        )
        return LlamaLabsClient(api_url="https://test.llamalabs.ai", api_key="test-key")


def test_agents(llamalabs_client):
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.llamalabs.ai/graphql",
            json={"data": {"allAgents": [{"handle": "test", "name": "Test Agent"}]}},
        )
        assert llamalabs_client.get_agents() == {
            "test": {"handle": "test", "name": "Test Agent"}
        }


def test_sessions(llamalabs_client):
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.llamalabs.ai/graphql",
            json={
                "data": {
                    "allSessions": [{"handle": "test-handle", "name": "Test Session"}]
                }
            },
        )
        assert llamalabs_client.get_sessions() == ["test-handle"]


def test_get_session():
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.llamalabs.ai/graphql",
            json={
                "data": {
                    "sessionByHandle": {
                        "handle": "test-handle",
                    }
                }
            },
        )
        client = LlamaLabsClient(
            api_url="https://test.llamalabs.ai",
            api_key="test-key",
        )
        session = client.get_session("test-handle")

        m.post(
            "https://test.llamalabs.ai/graphql",
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
