import time
from typing import Generator

from fastapi import FastAPI

from llamalabs import Agent
from llamalabs import AgentQuery


class SimpleAgent(Agent):
    """This is an example of a simple Llama Labs Agent that always replies "Hi from SimpleAgent"
    to any query it receives.

    To run this agent, use:
        uvicorn examples.agents.simpleagent:app --reload

    An example query to the agent might look like this:
        curl -v -X POST -H "Content-Type: application/json" --data '{"message": {"text": "Howdy"}}' http://localhost:8000
    """

    def query(self, query: AgentQuery) -> Generator[str, None, None]:
        print(f"SimpleAgent got query: {query}")

        # Agents can return multiple replies to a single query, which we demonstrate here.
        for _ in range(3):
            yield "Hi from SimpleAgent"
            time.sleep(1)


# This code allows the Agent to be run as a standalone FastAPI handler using uvicorn.
app = FastAPI()
agent = SimpleAgent()
app.include_router(agent.router)
