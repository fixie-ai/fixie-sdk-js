import json
import os

import fastapi
import pytest
import yaml
from fastapi import testclient

from fixieai.agents import api
from fixieai.agents import exceptions
from fixieai.agents import standalone
from fixieai.agents import token


@pytest.fixture(autouse=True)
def mock_token_verifier(mocker):
    return mocker.patch.object(
        token.VerifiedTokenClaims,
        "from_token",
        return_value=token.VerifiedTokenClaims(
            agent_id="fake agent id", is_anonymous=False, token="fake token"
        ),
    )


def mock_handle_message_single(query):
    return query.text.upper()


def mock_handle_message_stream(query) -> api.AgentResponseGenerator:
    yield api.AgentResponse(api.Message(query.text.upper()))


def mock_handle_message_stream_exception(query) -> api.AgentResponseGenerator:
    yield api.AgentResponse(api.Message(query.text.upper()))
    raise ValueError("Fail!")


@pytest.fixture
def standalone_agent_single(mocker):
    mocker.patch.dict(os.environ, {"FIXIE_ALLOWED_AGENT_ID": "fake agent id"})
    return standalone.StandaloneAgent(
        handle_message=mock_handle_message_single, sample_queries=["sample query"]
    )


@pytest.fixture
def standalone_agent_stream(mocker):
    mocker.patch.dict(os.environ, {"FIXIE_ALLOWED_AGENT_ID": "fake agent id"})
    return standalone.StandaloneAgent(
        handle_message=mock_handle_message_stream, sample_queries=["sample query"]
    )


def test_standalone_handshake(standalone_agent_single):
    client = testclient.TestClient(standalone_agent_single.app())

    response = client.get("/", headers={"Authorization": "Bearer fixie-test-token"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/yaml"
    yaml_content = yaml.load(response.content, Loader=yaml.Loader)
    assert yaml_content == {"sample_queries": ["sample query"], "type": "standalone"}


# call this test with both the standalone_agent_single and standalone_agent_stream fixtures
def test_standalone_query_single(standalone_agent_single):
    _standalone_query(standalone_agent_single)


def test_standalone_query_stream_exception(mocker):
    def _gen(query):
        yield api.AgentResponse(api.Message(query.text.upper()))
        raise ValueError("Fail!")

    mocker.patch.dict(os.environ, {"FIXIE_ALLOWED_AGENT_ID": "fake agent id"})
    agent = standalone.StandaloneAgent(
        handle_message=_gen, sample_queries=["sample query"]
    )
    client = testclient.TestClient(agent.app(), raise_server_exceptions=False)

    with client.stream(
        "POST",
        "/",
        headers={"Authorization": "Bearer fixie-test-token"},
        json={"message": {"text": "sample text", "embeds": {}}},
    ) as response:
        assert response.status_code == 200
        [response1, response2] = response.iter_lines()
        assert json.loads(response1) == {
            "message": {"text": "SAMPLE TEXT", "embeds": {}},
            "error": None,
        }
        response2_dict = json.loads(response2)
        assert (
            response2_dict["message"]["text"]
            == exceptions.UNHANDLED_EXCEPTION_RESPONSE_TEXT
        )
        assert response2_dict["error"]["code"] == "ERR_AGENT_UNHANDLED_EXCEPTION"
        assert (
            response2_dict["error"]["message"]
            == "An unhandled exception occurred while processing the request."
        )
        assert "ValueError: Fail!\n" in response2_dict["error"]["details"]["traceback"]


def _standalone_query(agent: standalone.StandaloneAgent):
    client = testclient.TestClient(agent.app())

    response = client.post(
        "/",
        headers={"Authorization": "Bearer fixie-test-token"},
        json={"message": {"text": "sample text", "embeds": {}}},
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "message": {"text": "SAMPLE TEXT", "embeds": {}},
        "error": None,
    }


def test_invalid_token(standalone_agent_single, mock_token_verifier):
    mock_token_verifier.return_value = None

    fast_api = fastapi.FastAPI()
    fast_api.include_router(standalone_agent_single.api_router())
    client = testclient.TestClient(fast_api, raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}
    response = client.post("/", json={"message": {"text": "Howdy"}}, headers=headers)
    assert response.status_code == 403
