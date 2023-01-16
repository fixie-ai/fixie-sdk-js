import pytest
import requests_mock

from fixie.client import FixieClient


@pytest.fixture
def fixie_client():
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.fixie.ai/graphql",
            json={"data": {"createSession": {"session": {"handle": "test-handle"}}}},
        )
        return FixieClient(api_url="https://test.fixie.ai", api_key="test-key")


def test_agents(fixie_client):
    with requests_mock.Mocker() as m:
        m.post(
            "https://test.fixie.ai/graphql",
            json={"data": {"allAgents": [{"handle": "test", "name": "Test Agent"}]}},
        )
        assert fixie_client.get_agents() == {
            "test": {"handle": "test", "name": "Test Agent"}
        }


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
        client = FixieClient(
            api_url="https://test.fixie.ai",
            api_key="test-key",
            session_id="test-handle",
        )
        assert client.get_messages() == [{"id": 1, "text": "Test message"}]
