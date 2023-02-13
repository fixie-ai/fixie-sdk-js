import fastapi
from fastapi import testclient

from fixie import agents

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


def test_simple_agent_handshake():
    fast_api = fastapi.FastAPI()
    fast_api.include_router(agent.api_router())
    client = testclient.TestClient(fast_api)
    response = client.get("/")
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "base_prompt": agent.base_prompt,
        "few_shots": agent.few_shots,
    }


def test_simple_agent_func_calls():
    fast_api = fastapi.FastAPI()
    fast_api.include_router(agent.api_router())
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
