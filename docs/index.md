# Llama Labs

Llama Labs is a platform for building applications using Large Language
Models. With Llama Labs, you can write apps that communicate, in natural
language, with one or more *agents* that can access individual APIs or
sources of data, such as GitHub, Google Calendar, or a database.

You can access the Llama Labs web interface at [app.llamalabs.ai](https://app.llamalabs.ai). Using the Llama Labs SDK allows you to connect your own
applications to the Llama Labs platform, either as a client, or by
building custom agents that plug into the platform.

---

# Getting started

Install the Llama Labs SDK using pip:

```shell
$ pip install llamalabs
```

Now, let's get started:

```pycon
>>> import llamalabs
>>> client = llamalabs.client.client.LlamaLabsClient()
```

