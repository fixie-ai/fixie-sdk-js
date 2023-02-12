import fastapi
from fastapi import testclient

from fixie import agents


class SimpleAgent(agents.CodeShotAgent):
    agent_id = "simple_agent"
    BASE_PROMPT = "I am a simple dummy agent."
    FEW_SHOTS = [
        """Q: Sample query 1
           Ask Func[simple1]: Simple argument
           Func[simple1] says: Simple response
           A: Simple final response""",
        """Q: Sample query 2
           Ask Func[simple2]: Simple argument
           Func[simple2] says: Simple response
           A: Simple final response""",
    ]

    def simple1(self, query: agents.AgentQuery) -> str:
        return "Simple response 1"

    def simple2(self, query: agents.AgentQuery) -> str:
        return "Simple response 2"


def test_simple_agent_handshake():
    agent = SimpleAgent()
    fast_api = fastapi.FastAPI()
    fast_api.include_router(agent.api_router())
    client = testclient.TestClient(fast_api)
    response = client.get("/")
    assert response.status_code == 200
    json = response.json()
    assert json["agent_id"] == agent.agent_id
    assert json["base_prompt"] == agent.BASE_PROMPT
    assert json["few_shots"] == agent.FEW_SHOTS


def test_simple_agent_func_calls():
    agent = SimpleAgent()
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

    # Test non-existing Func[] returns 404: Not Found
    response = client.post(
        "/prefix/path/non_existing_func", json={"message": {"text": "Howdy"}}
    )
    assert response.status_code == 404

    # Test Func[simple1] with bad arguments returns 422: Unprocessable Entity
    response = client.post("/simple1", json={"message": {"ttt": "Howdy"}})
    assert response.status_code == 422

    # Test Func[__init__] 403: Forbidden
    response = client.post("/__init__", json={"message": {"text": "Howdy"}})
    assert response.status_code == 403
