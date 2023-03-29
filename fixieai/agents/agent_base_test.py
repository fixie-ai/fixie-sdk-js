import os

import fastapi
import pytest
import yaml
from fastapi import testclient
from pydantic import dataclasses as pydantic_dataclasses

import fixieai
from fixieai import agents
from fixieai.agents import agent_base

agent_id = "dummy"


@pytest.fixture(autouse=True)
def mock_token_verifier(mocker):
    return mocker.patch.object(
        agent_base.VerifiedTokenClaims,
        "from_token",
        return_value=agent_base.VerifiedTokenClaims(agent_id="fake agent id"),
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

    return agent


def test_simple_agent_handshake(dummy_agent, mocker):
    fast_api = fastapi.FastAPI()
    fast_api.include_router(dummy_agent.api_router())

    client = testclient.TestClient(fast_api)

    # Use a small chunk size to exercise chunking logic
    mocker.patch.object(agent_base, "_RESPONSE_CHUNK_SIZE", 2)
    response = client.get("/", headers={"Authorization": "Bearer fixie-test-token"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/yaml"
    yaml_content = yaml.load(response.content, Loader=yaml.Loader)
    assert yaml_content == {"dummy_metadata": True}


def test_simple_agent_func_calls(dummy_agent, mock_token_verifier):
    fast_api = fastapi.FastAPI()
    fast_api.include_router(dummy_agent.api_router())

    client = testclient.TestClient(fast_api, raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test Func[simple1]
    response = client.post(
        "/simple1", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {"message": {"text": "Simple response 1", "embeds": {}}}
    mock_token_verifier.assert_called_once_with(
        "fixie-test-token", dummy_agent._jwks_client, dummy_agent._allowed_agent_id
    )

    # Test Func[simple2]
    response = client.post(
        "/simple2", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {"message": {"text": "Simple response 2", "embeds": {}}}

    # Test Func[custom]
    response = client.post(
        "/custom", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {"message": {"text": "Simple response custom", "embeds": {}}}

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


def good_duck_typed_func1(query):
    return "test"


def good_duck_typed_func2(query, user_storage):
    return "test"


def good_duck_typed_func3(user_storage, oauth_handler, query):
    return "test"


def bad_duck_typed_func1(*query):
    return "test"


def bad_duck_typed_func2(**user_storage):
    return "test"


def bad_duck_typed_func3(query, *user_storage):
    return "test"


def good_typed_func1(query: fixieai.Message) -> fixieai.AgentResponse:
    return fixieai.AgentResponse(fixieai.Message("test"))


def good_typed_func2(query: fixieai.Message) -> fixieai.Message:
    return fixieai.Message("test")


def good_typed_func3(user_storage: fixieai.UserStorage) -> str:
    return "test"


def good_typed_func4(
    user_storage: fixieai.UserStorage, oauth_handler: fixieai.OAuthHandler
) -> fixieai.Message:
    return fixieai.Message("test")


def good_semi_typed_func1(query: fixieai.Message):
    ...


def good_semi_typed_func2(query) -> str:
    return "test"


def good_semi_typed_func3(user_storage, query: fixieai.Message):
    ...


def good_semi_typed_func4(user_storage, oauth_handler) -> str:
    return "test"


def bad_typed_func1(query: str) -> str:
    return "test"


def bad_typed_func2(query: int) -> str:
    return "test"


def test_registering_good_and_bad_typed_funcs(dummy_agent):
    good_funcs = [
        good_typed_func1,
        good_typed_func2,
        good_typed_func3,
        good_typed_func4,
        good_duck_typed_func1,
        good_duck_typed_func2,
        good_duck_typed_func3,
        good_semi_typed_func1,
        good_semi_typed_func2,
        good_semi_typed_func3,
        good_semi_typed_func4,
    ]
    bad_funcs = [
        bad_typed_func1,
        bad_typed_func2,
        bad_duck_typed_func1,
        bad_duck_typed_func2,
        bad_duck_typed_func3,
    ]
    for good_func in good_funcs:
        dummy_agent.register_func(good_func)
        assert dummy_agent._funcs[good_func.__name__] == good_func

    for bad_func in bad_funcs:
        with pytest.raises(TypeError):
            dummy_agent.register_func(bad_func)


def test_registering_func_with_custom_name(dummy_agent):
    dummy_agent.register_func(good_typed_func1, func_name="name1")
    dummy_agent.register_func(good_typed_func2, func_name="name2")
    dummy_agent.register_func(good_typed_func3, func_name="name3")
    assert dummy_agent._funcs["name1"] == good_typed_func1
    assert dummy_agent._funcs["name2"] == good_typed_func2
    assert dummy_agent._funcs["name3"] == good_typed_func3


def test_invalid_token(dummy_agent, mock_token_verifier):
    mock_token_verifier.return_value = None

    fast_api = fastapi.FastAPI()
    fast_api.include_router(dummy_agent.api_router())
    client = testclient.TestClient(fast_api, raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}
    response = client.post(
        "/simple1", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 403
