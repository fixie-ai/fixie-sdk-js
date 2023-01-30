import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from llamalabs import Agent
from llamalabs import AgentQuery


class SimpleAgent(Agent):
    """A simple Agent for testing."""

    def query(self, query: AgentQuery):
        logging.info(f"MDW: query called!!!")
        #        yield AgentResponse(message="Test response", response_type=AgentResponseType.RESPONSE)
        yield "Test response"


def test_agent():
    app = FastAPI()
    agent = SimpleAgent()
    app.include_router(agent.router)
    client = TestClient(app)
    response = client.post("/", json={"message": {"text": "Howdy"}})
    logging.info(response.content)
    assert response.status_code == 200
    assert response.json()["message"] == "Test response"
    assert response.json()["response_type"] == "response"
