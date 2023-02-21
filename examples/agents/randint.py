#!/usr/bin/env python3

# This is an example Fixie Agent that generates random integers.

import random
import fixieai

BASE_PROMPT = "I am a simple agent that generates a random number between two given values."
FEW_SHOTS = """
Q: Generate a random number between 0 and 19.
Ask Func[genrand]: 0, 19
Func[genrand] says: 17
A: The random number is 17.

Q: Generate a random value from 5 to 10, inclusive.
Ask Func[genrand]: 5, 10
Func[genrand] says: 8
A: The random number is 8.
"""

agent = fixieai.CodeShotAgent(BASE_PROMPT, FEW_SHOTS)

@agent.register_func()
def genrand(query: fixieai.AgentQuery) -> str:
    low, high = query.message.text.replace(" ", "").split(",")
    return str(random.randint(int(low), int(high)))

agent.serve("randint")
