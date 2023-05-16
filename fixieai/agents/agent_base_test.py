import os

import pytest
import yaml
from fastapi import testclient
from pydantic import dataclasses as pydantic_dataclasses

import fixieai
from fixieai import agents
from fixieai.agents import agent_base
from fixieai.agents import exceptions
from fixieai.agents import token

agent_id = "dummy"


@pytest.fixture(autouse=True)
def mock_token_verifier(mocker):
    return mocker.patch.object(
        token.VerifiedTokenClaims,
        "from_token",
        return_value=token.VerifiedTokenClaims(
            agent_id="fake agent id", is_anonymous=False, token="fake token"
        ),
    )


@pytest.fixture
def dummy_agent(mocker):
    mocker.patch.dict(os.environ, {"FIXIE_ALLOWED_AGENT_ID": "fake agent id"})

    @pydantic_dataclasses.dataclass
    class DummyMetadata:
        dummy_metadata: bool = True

    class DummyAgent(agents.AgentBase):
        def metadata(self):
            return DummyMetadata()

        def validate(self):
            pass

    agent = DummyAgent(
        oauth_params=fixieai.OAuthParams(
            client_id="dummy",
            client_secret="dummy",
            auth_uri="dummy",
            token_uri="dummy",
            scopes=["dummy"],
        ),
    )

    @agent.register_func
    def simple1(query: agents.Message) -> str:
        return "Simple response 1"

    @agent.register_func()
    def simple2(query: agents.Message):
        return "Simple response 2"

    @agent.register_func(func_name="custom")
    def simple3(query):
        return "Simple response custom"

    @agent.register_func()
    def unhandled_exception(query):
        raise ValueError("Func failed!")

    @agent.register_func()
    def agent_exception(query):
        raise exceptions.AgentException(
            response_message="Agent exception!",
            error_message="My exception occurred.",
            error_code="ERR_MY_ERROR_CODE",
            http_status_code=400,
            detail=1,
        )

    return agent


def test_simple_agent_handshake(dummy_agent, mocker):
    client = testclient.TestClient(dummy_agent.app())

    # Use a small chunk size to exercise chunking logic
    mocker.patch.object(agent_base, "_RESPONSE_CHUNK_SIZE", 2)
    response = client.get("/", headers={"Authorization": "Bearer fixie-test-token"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/yaml"
    yaml_content = yaml.load(response.content, Loader=yaml.Loader)
    assert yaml_content == {"dummy_metadata": True}


def test_simple_agent_func_calls(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test Func[simple1]
    response = client.post(
        "/simple1", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "message": {"text": "Simple response 1", "embeds": {}},
        "error": None,
    }
    mock_token_verifier.assert_called_once_with(
        "fixie-test-token", dummy_agent._jwks_client, dummy_agent._allowed_agent_id
    )

    # Test Func[simple2]
    response = client.post(
        "/simple2", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "message": {"text": "Simple response 2", "embeds": {}},
        "error": None,
    }

    # Test Func[custom]
    response = client.post(
        "/custom", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "message": {"text": "Simple response custom", "embeds": {}},
        "error": None,
    }

    # Test non-existing Func[] returns 404: Not Found
    response = client.post(
        "/simple3", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 404

    # Test Func[simple1] with bad arguments returns 422: Unprocessable Entity
    response = client.post(
        "/simple1", json={"message": {"ttt": "Howdy"}}, headers=headers
    )
    assert response.status_code == 422

    # Test Func[__init__] 404: Not Found
    response = client.post(
        "/__init__", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 404

    # Test Func without auth header returns 401: Unauthorized
    response = client.post("/simple1", json={"message": {"text": "Howdy"}})
    assert response.status_code == 403


def test_simple_agent_func_failure(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test Func[unhandled_exception]
    response = client.post(
        "/unhandled_exception", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 500
    json = response.json()
    assert json["message"]["text"] == exceptions.UNHANDLED_EXCEPTION_RESPONSE_TEXT
    assert "ValueError: Func failed!\n" in json["error"]["details"]["traceback"]


def test_simple_agent_func_custom_failure(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test Func[unhandled_exception]
    response = client.post(
        "/agent_exception", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 400
    json = response.json()
    assert json["message"]["text"] == "Agent exception!"
    assert json["error"]["details"]["detail"] == 1


def test_registering_func_with_custom_name(dummy_agent):
    dummy_agent.register_func(lambda query: "1", func_name="name1")
    dummy_agent.register_func(lambda query: "2", func_name="name2")
    dummy_agent.register_func(lambda query: "3", func_name="name3")

    def invoke_func(name: str):
        responses = dummy_agent._funcs[name](
            fixieai.AgentQuery(fixieai.Message("test")), "agent-id"
        )
        return next(iter(responses)).message.text

    assert invoke_func("name1") == "1"
    assert invoke_func("name2") == "2"
    assert invoke_func("name3") == "3"


def test_invalid_token(dummy_agent, mock_token_verifier):
    mock_token_verifier.return_value = None

    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}
    response = client.post(
        "/simple1", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 403
