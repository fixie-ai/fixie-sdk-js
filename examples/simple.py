#!/usr/bin/env python3

# This is a simple example of how to use the Fixie Python SDK.

import fixie

# First create a client. This requires setting the FIXIE_API_KEY
# environment variable to your API key, which can be obtained from
# your profile page on https://app.fixie.ai.
client = fixie.FixieClient()

# Get the list of Agents registered with the Fixie service.
agents = client.agents()
for agent_id, agent in agents.items():
    print(f"{agent_id}: {agent['name']}")

# Create a new Playground.
playground = fixie.Playground(client.gqlclient)

# Send it some queries.
result = playground.query("How many issues are assigned to mdwelsh?")
print(result)

result = playground.query("Show them to me")
print(result)
