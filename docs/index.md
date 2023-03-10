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

Install the Fixie SDK using pip:

```shell
$ pip install fixieai
```

Once installed, run `fixie auth` to authenticate with Fixie and start building.
Now, import the Fixie SDK and use it to run queries:

```pycon
>>> import fixieai
>>> response = fixieai.query("How many countries start with the letter R ?")
>>> print(response)
```

# Agent Examples

Agents are at the heart of the Fixie ecosystem, and we make it easy to build and contribute your own. To get started you can scaffold out a default agent by running: `fixie init`. For more examples
check out [Building Fixie Agents](agents.md) and our [examples repo](https://github.com/fixie-ai/fixie-examples).

# Documentation

Check out the links below for more information on how to
get started using Fixie.

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