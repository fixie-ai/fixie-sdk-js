"""This is an example of a simple Fixie Agent that tosses a coin.

An example query to the local agents might look like this:
    curl -v -X GET http://localhost:8181
this should return the agent prompt, the fewshots, and other agent metadata

An example query to the hosted agents might look like this:
    curl -v -X POST http://localhost:8181 \
        -H "Content-Type: application/json" \
        --data '{"message": {"text": "flip a coin"}}'
"""
import random

import fixie.agents

BASE_PROMPT = "I am a simple agent that tosses a coin."
FEW_SHOTS = """
Q: Toss a coin.
Func[coin] says: heads
A: It's heads!

Q: Toss a coin 3 times.
Func[coin] says: heads
Func[coin] says: heads
Func[coin] says: tails
A: It was heads the first 2 times and tails the last time!
"""

agent = fixie.agents.CodeShotAgent(BASE_PROMPT, FEW_SHOTS)


@agent.register_func()
def coin(self, query: fixie.agents.AgentQuery) -> str:
    return random.choice(["heads", "tails"])


agent.serve("toss_a_coin", host="0.0.0.0", port=8181)
