from unittest import mock

import fastapi
import pytest
import yaml
from fastapi import testclient

import fixieai
from fixieai import agents
from fixieai.agents import code_shot

agent_id = "dummy"
BASE_PROMPT = "I am a simple dummy agent."
FEW_SHOTS = """
Q: Sample query 1
Ask Func[simple1]: Simple argument
Func[simple1] says: Simple response
A: Simple final response

Q: Sample query 2
Ask Func[simple2]: Simple argument
Func[simple2] says: Simple response
A: Simple final response
"""


@pytest.fixture
def dummy_agent():
    agent = agents.CodeShotAgent(
        agent_id,
        BASE_PROMPT,
        FEW_SHOTS,
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

    agent._verify_token = mock.Mock(return_value=True)
    return agent


def test_simple_agent_handshake(dummy_agent):
    fast_api = fastapi.FastAPI()
    fast_api.include_router(dummy_agent.api_router())
    client = testclient.TestClient(fast_api)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/yaml"
    yaml_content = yaml.load(response.content, Loader=yaml.Loader)
    assert yaml_content == {
        "base_prompt": dummy_agent.base_prompt,
        "few_shots": dummy_agent.few_shots,
    }


def test_simple_agent_func_calls(dummy_agent):
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
    dummy_agent._verify_token.assert_called_once_with("fixie-test-token")

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


def test_split_few_shots():
    few_shots_list = code_shot._split_few_shots(FEW_SHOTS)
    assert few_shots_list == [
        """
Q: Sample query 1
Ask Func[simple1]: Simple argument
Func[simple1] says: Simple response
A: Simple final response""",
        """Q: Sample query 2
Ask Func[simple2]: Simple argument
Func[simple2] says: Simple response
A: Simple final response""",
    ]


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
