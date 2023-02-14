import fastapi
import pytest
from fastapi import testclient

import fixieai
from fixieai import agents
from fixieai.agents import code_shot

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
    agent = agents.CodeShotAgent(BASE_PROMPT, FEW_SHOTS)

    @agent.register_func
    def simple1(query: agents.AgentQuery) -> str:
        return "Simple response 1"

    @agent.register_func()
    def simple2(query: agents.AgentQuery):
        return "Simple response 2"

    @agent.register_func(func_name="custom")
    def simple3(query):
        return "Simple response custom"

    return agent


def test_simple_agent_handshake(dummy_agent):
    fast_api = fastapi.FastAPI()
    fast_api.include_router(dummy_agent.api_router())
    client = testclient.TestClient(fast_api)
    response = client.get("/")
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "base_prompt": dummy_agent.base_prompt,
        "few_shots": dummy_agent.few_shots,
    }


def test_simple_agent_func_calls(dummy_agent):
    fast_api = fastapi.FastAPI()
    fast_api.include_router(dummy_agent.api_router())
    client = testclient.TestClient(fast_api, raise_server_exceptions=False)

    # Test Func[simple1]
    response = client.post("/simple1", json={"message": {"text": "Howdy"}})
    assert response.status_code == 200
    json = response.json()
    assert json == {"message": {"text": "Simple response 1", "embeds": {}}}

    # Test Func[simple2]
    response = client.post("/simple2", json={"message": {"text": "Howdy"}})
    assert response.status_code == 200
    json = response.json()
    assert json == {"message": {"text": "Simple response 2", "embeds": {}}}

    # Test Func[custom]
    response = client.post("/custom", json={"message": {"text": "Howdy"}})
    assert response.status_code == 200
    json = response.json()
    assert json == {"message": {"text": "Simple response custom", "embeds": {}}}

    # Test non-existing Func[] returns 404: Not Found
    response = client.post("/simple3", json={"message": {"text": "Howdy"}})
    assert response.status_code == 404

    # Test Func[simple1] with bad arguments returns 422: Unprocessable Entity
    response = client.post("/simple1", json={"message": {"ttt": "Howdy"}})
    assert response.status_code == 422

    # Test Func[__init__] 404: Not Found
    response = client.post("/__init__", json={"message": {"text": "Howdy"}})
    assert response.status_code == 404


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


def good_duck_typed_func(x):
    return "test"


def bad_duck_typed_func1(x, y):
    return "test"


def bad_duck_typed_func2(*x):
    return "test"


def bad_duck_typed_func3(**x):
    return "test"


def good_typed_func1(x: fixieai.AgentQuery) -> fixieai.AgentResponse:
    return fixieai.AgentResponse(fixieai.Message("test"))


def good_typed_func2(x: fixieai.AgentQuery) -> fixieai.Message:
    return fixieai.Message("test")


def good_typed_func3(x: fixieai.AgentQuery) -> str:
    return "test"


def good_semi_typed_func4(x: fixieai.AgentQuery):
    ...


def good_semi_typed_func5(x) -> str:
    return "test"


def bad_typed_func1(x: str) -> str:
    return "test"


def bad_typed_func2(x: int) -> str:
    return "test"


def test_registering_func(dummy_agent):
    dummy_agent.register_func(good_typed_func1, func_name="name1")
    dummy_agent.register_func(good_typed_func2, func_name="name2")
    dummy_agent.register_func(good_typed_func3, func_name="name3")
    assert dummy_agent._funcs["name1"] == good_typed_func1
    assert dummy_agent._funcs["name2"] == good_typed_func2
    assert dummy_agent._funcs["name3"] == good_typed_func3

    dummy_agent.register_func(good_duck_typed_func)
    assert dummy_agent._funcs["good_duck_typed_func"] == good_duck_typed_func

    dummy_agent.register_func(good_semi_typed_func4)
    assert dummy_agent._funcs["good_semi_typed_func4"] == good_semi_typed_func4

    dummy_agent.register_func(good_semi_typed_func5)
    assert dummy_agent._funcs["good_semi_typed_func5"] == good_semi_typed_func5

    with pytest.raises(TypeError):
        dummy_agent.register_func(bad_duck_typed_func1)
    with pytest.raises(TypeError):
        dummy_agent.register_func(bad_duck_typed_func2)
    with pytest.raises(TypeError):
        dummy_agent.register_func(bad_duck_typed_func3)
    with pytest.raises(TypeError):
        dummy_agent.register_func(bad_typed_func1)
    with pytest.raises(TypeError):
        dummy_agent.register_func(bad_typed_func2)
