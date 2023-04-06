# Fixie Developer Portal

[Fixie](https://fixie.ai) is a platform for building applications using large language models. With Fixie, you can create apps that communicate in natural language with one or more *agents* that access individual APIs or sources of data, such as GitHub, Google Calendar, or a database.

Access the Fixie web interface at [app.fixie.ai](https://app.fixie.ai). The Fixie SDK allows you to connect your applications to the Fixie platform, either as a client or by building custom agents that plug into the platform.

Learn more about Fixie at [https://fixie.ai](https://fixie.ai).

**Fixie Developer Preview**: Fixie is currently available as a Developer Preview. During this time, Fixie is free to use; however, there is a limit on the number of queries per user per day. Please see [Fixie Developer Preview](developer-preview.md) for more information.

**Need help?**: The best way to contact us and get support is to join our [Discord server](https://discord.gg/MsKAeKF8kU).

---

# Getting Started

1. Verify access to [app.fixie.ai](http://app.fixie.ai) with your Google or GitHub email.
1. Install the Fixie CLI using `pip install fixieai` and run `fixie auth` to ensure successful authentication.
1. Fork the [examples repo](https://github.com/fixie-ai/fixie-examples).

## Demo an agent
1. Choose any example agent
1. `cd` into the directory
1. Run `fixie agent deploy`

You can now test the agent through the following methods:
* Run `fixie console -a username/agent_name` and input a test query.
* Run `fixie console` and then @ your specific agent (e.g., `@username/agent_name this is the query`).
* Talk to deployed agents directly at [app.fixie.ai](http://app.fixie.ai).
* Interact with the agent programmatically:
  ```py
  import fixieai
  response = fixieai.query("How many countries start with the letter R ?")
  print(response)
  ```

For local development and testing, run your agent locally with `fixie agent serve`. This is useful for debugging issues. This will create a tunnel to your local machine. After running serve, open a new terminal window and talk to the agent via `fixie console`.

# agent Examples

agents are at the heart of the Fixie ecosystem, and we make it easy to build and contribute your own. Start by scaffolding a default agent with `fixie init`. For more examples, check out [Building Fixie agents](agents.md) and our [examples repo](https://github.com/fixie-ai/fixie-examples).

# Documentation

Explore the links below for more information on getting started with Fixie.

## Tutorials

* [Fixie Architecture Overview](architecture.md)
* [agent Quickstart](agent-quickstart.md)
* [Building Fixie agents](agents.md)
* [agent Protocol](agent-protocol.md)

## Reference

* [Fixie CLI Reference](cli.md)
* [Python Client API](python-client-api.md)
* [Python agent API](python-agent-api.md)
* [Fixie GraphQL API Reference](https://app.fixie.ai/static/docs/index.html)