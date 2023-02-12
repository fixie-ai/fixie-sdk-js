#!/usr/bin/env python3

# This is a simple example of how to use the Fixie Python SDK.

import requests

import fixie.client.client as client

# Get the list of Agents registered with the Fixie service.
agents = client.agents()
for agent_id, agent in agents.items():
    print(f"{agent_id}: {agent['name']}")

# Send it some queries.
result = client.query("How many issues are assigned to mdwelsh?")
print(result)

result = client.query("Show them to me")
print(result)

# Generate an image.
result = client.query("Generate an image of a cute red panda")
print(result)

# Fetch the image and save it to a file.
embeds = client.embeds()
embed_url = embeds[0]["embed"]["url"]
r = requests.get(embed_url)
r.raise_for_status()
with open("panda.png", "wb") as f:
    f.write(r.content)
    print("Saved panda.png")
