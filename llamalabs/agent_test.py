import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from llamalabs import Agent
from llamalabs import AgentQuery
from llamalabs import AgentResponse
from llamalabs import AgentResponseType


class SimpleAgent(Agent):
    """A simple Agent for testing."""

    def query(self, query: AgentQuery):
        yield AgentResponse(
            message="Intermediate status",
            response_type=AgentResponseType.STATUS_MIDDLE_PROMPT,
        )
        yield "Test response"


def test_agent():
    app = FastAPI()
    agent = SimpleAgent()
    app.include_router(agent.router)
    client = TestClient(app)
    response = client.post("/", json={"message": {"text": "Howdy"}})
    assert response.status_code == 200
    responses = response.content.split(b"\r\n")
    lines = []
    for line in responses:
        if line:
            lines.append(json.loads(line))
    assert lines[0]["message"] == "Intermediate status"
    assert lines[0]["response_type"] == "status_middle_prompt"
    assert lines[1]["message"] == "Test response"
    assert lines[1]["response_type"] == "response"


class DoubleResponseAgent(Agent):
    """This agent incorrectly yields two RESPONSE messages on each query."""

    def query(self, query: AgentQuery):
        yield "Test response one"
        yield "Test response two"


def test_double_response_agent():
    app = FastAPI()
    agent = DoubleResponseAgent()
    app.include_router(agent.router)
    client = TestClient(app)
    # The FastAPI TestClient directly raises exceptions from the query handler, rather
    # than emulating an HTTP transaction with a non-200 repsonse code.
    with pytest.raises(ValueError):
        response = client.post("/", json={"message": {"text": "Howdy"}})
