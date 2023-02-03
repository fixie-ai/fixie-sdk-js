import random

import llamalabs.agents


class SimpleAgent(llamalabs.agents.CodeShotAgent):
    """This is an example of a simple Llama Labs Agent that tosses a coin.

    To run this agents, use:
        agent = SimpleAgent()
        agent.serve()

    An example query to the agents might look like this:
        curl -v -X POST http://localhost:8000 \
            -H "Content-Type: application/json" \
            --data '{"message": {"text": "Howdy"}}'
    """

    agent_id = "toss_a_coin"
    BASE_PROMPT = "I am a simple agent that tosses a coin."
    FEW_SHOTS = [
        """Q: Toss a coin.
           Func[coin] says: heads
           A: It's heads!""",
        """Q: Toss a coin 3 times.
           Func[coin] says: heads
           Func[coin] says: heads
           Func[coin] says: tails
           A: It was heads the first 2 times and tails the last time!""",
    ]

    def coin(self, query: llamalabs.agents.AgentQuery) -> str:
        return random.choice(["heads", "tails"])


agent = SimpleAgent()
agent.serve(host="0.0.0.0", port=8181)
