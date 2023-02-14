"""This is an example of a simple Fixie Agent that tosses a coin.

An example query to a local agent might look like this:
    curl -v -X GET http://localhost:8181
this should return the agent prompt, the fewshots, and other agent metadata
"""
import random

import fixieai

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

agent = fixieai.CodeShotAgent(BASE_PROMPT, FEW_SHOTS)


@agent.register_func()
def coin(query: fixieai.AgentQuery) -> str:
    return random.choice(["heads", "tails"])


agent.serve("coin", host="0.0.0.0", port=8181)
