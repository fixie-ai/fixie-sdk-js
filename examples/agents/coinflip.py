"""This is an example of a simple Fixie Agent that flips a coin."""
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

# Create the Agent with the base prompt and few shots.
agent = fixieai.CodeShotAgent(BASE_PROMPT, FEW_SHOTS)

# The coin() function can be invoked by the Agent.
@agent.register_func()
def coin(query: fixieai.AgentQuery) -> str:
    return random.choice(["heads", "tails"])

# Start the Agent. The name "coinflip" must match the handle of
# the Agent that you create when you register the Agent with Fixie:
# https://app.fixie.ai/agents/new
agent.serve("coinflip")
