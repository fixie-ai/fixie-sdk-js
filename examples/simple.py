#!/usr/bin/env python3

# This is a simple example of how to use the Fixie Python SDK.

import fixie

# Get the list of Agents registered with the Fixie service.
agents = fixie.agents()
for agent_id, agent in agents.items():
    print(f"{agent_id}: {agent['name']}")

# Send it some queries.
result = fixie.query("How many issues are assigned to mdwelsh?")
print(result)

result = fixie.query("Show them to me")
print(result)
