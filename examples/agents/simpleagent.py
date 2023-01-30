import time

from fastapi import FastAPI

from llamalabs import Agent
from llamalabs import AgentQuery
from llamalabs import AgentResponse


class SimpleAgent(Agent):
    def query(self, query: AgentQuery):
        print(f"SimpleAgent got query: {query}")
        for _ in range(3):
            yield AgentResponse(message="Hi from SimpleAgent")
            time.sleep(1)


app = FastAPI()
agent = SimpleAgent()
app.include_router(agent.router)
