# Fixie Developer Portal

[Fixie](https://fixie.ai) is a platform for building applications using Large Language
Models. With Fixie, you can write apps that communicate, in natural
language, with one or more *Agents* that can access individual APIs or
sources of data, such as GitHub, Google Calendar, or a database.

You can access the Fixie web interface at [app.fixie.ai](https://app.fixie.ai).
Using the Fixie SDK allows you to connect your own
applications to the Fixie platform, either as a client, or by
building custom agents that plug into the platform.

To learn more about Fixie, check us out at [https://fixie.ai](https://fixie.ai).

---

# Getting started

* 1. Verify you can access [app.fixie.ai](http://app.fixie.ai) with your Google or GitHub email
* 2. Install the fixie CLI with `pip install fixieai` and run `fixie auth` to ensure your are successfully authenticated
* 3. Fork the [examples repo](https://github.com/fixie-ai/fixie-examples)
* 4. Choose any of the example agents, `cd` into the directory, and run `fixie agent deploy`
* 5. Test that agent by running `fixie console -a username/agent_name` and inputting a test query. You can also run `fixie console` and then @ your specific agent (e.g. `@username/agent_name this is the query`)
* 6. You can also talk to deployed agents directly at [app.fixie.ai](http://app.fixie.ai)
* 7. For local development and testing, you can also run your agent locally with `fixie agent serve`. This is easier for debugging what’s happening when things go wrong. This will create a tunnel to your local machine. After running serve, open a new terminal window and talk to the agent just like in step 5.

Example of query using SDK:

```py
import fixieai
response = fixieai.query("How many countries start with the letter R ?")
print(response)
```

# Agent Examples

Agents are at the heart of the Fixie ecosystem, and we make it easy to build and contribute your own. To get started you can scaffold out a default agent by running: `fixie init`. For more examples
check out [Building Fixie Agents](agents.md) and our [examples repo](https://github.com/fixie-ai/fixie-examples).

# Documentation

Check out the links below for more information on how to get started using Fixie.

## Tutorials

* [Fixie Architecture Overview](architecture.md)
* [Agent Quickstart](agent-quickstart.md)
* [Building Fixie Agents](agents.md)
* [Agent Protocol](agent-protocol.md)

## Reference

* [Fixie CLI Reference](cli.md)
* [Python Client API](python-client-api.md)
* [Python Agent API](python-agent-api.md)
* [Fixie GraphQL API Reference](https://app.fixie.ai/static/docs/index.html)