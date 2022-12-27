import pytest
import requests_mock

from fixie.client import FixieClient


@pytest.fixture
def fixie_client():
    return FixieClient(api_host="test.fixie.ai", api_key="test-key")


def test_agents(fixie_client):
    with requests_mock.Mocker() as m:
        m.post(
            f"https://test.fixie.ai/graphql",
            json={"data": {"allAgents": [{"agentId": "test", "name": "Test Agent"}]}},
        )
        assert fixie_client.agents() == {
            "test": {"agentId": "test", "name": "Test Agent"}
        }


def test_playgrounds(fixie_client):
    with requests_mock.Mocker() as m:
        m.post(
            f"https://test.fixie.ai/graphql",
            json={
                "data": {
                    "allPlaygrounds": [
                        {"handle": "test-handle", "name": "Test Playground"}
                    ]
                }
            },
        )
        assert fixie_client.playgrounds() == {
            "test-handle": {"handle": "test-handle", "name": "Test Playground"}
        }


def test_get_playground(fixie_client):
    with requests_mock.Mocker() as m:
        m.post(
            f"https://test.fixie.ai/graphql",
            json={
                "data": {
                    "playgroundByHandle": {
                        "handle": "test-handle",
                        "name": "Test Playground",
                    }
                }
            },
        )
        assert fixie_client.get_playground("test-handle") == {
            "handle": "test-handle",
            "name": "Test Playground",
        }
