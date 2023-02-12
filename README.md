# Fixie SDK

This is the official Python SDK for Fixie.

## What is Fixie?

Fixie is a platform for building applications using large language models. In Fixie, an application
consists of a set of natural-language **queries** that are handled by one or more **agents**.
Each agent consists of a large language model coupled with some custom code to process or generate
data, or call out to external systems, such as databases or APIs. By composing agents together,
you can create complex workflows with very little code.

## Installation

The easiest way to install the Fixie SDK is via `pip`:
```
pip install fixie
```

## Get your API key

You can get your Fixie API key on your profile page at https://app.fixie.ai.
Set the value of the `FIXIE_API_KEY` environment variable to your API key:
```
$ export FIXIE_API_KEY=" -- your API key here -- "
```

## Using the Fixie CLI

The Fixie CLI tool lets you use Fixie interactively from the command line.
```
$ fixie console
Welcome to Fixie!
Connected to: https://app.fixie.ai/sessions/splashy-nimble-panda
fixie 🚲❯ Hello there
   @{'handle': 'user'}: Hello there
   @{'handle': 'user'}: Hello there
   @{'handle': 'fixie'}: Hello there
   @{'handle': 'fixie'}: Thought: This is not a question. I need to greet the user.
   @{'handle': 'fixie'}: Hi there! How can I help you?
1❯ Hi there! How can I help you?
fixie 🚲❯
```

## Client API

The simplest way to use Fixie from your app is to use the `fixie.query` method
to send a query:
```
import fixie
response = fixie.query("Hello there!")
print(response)
```

For more control, you can also create a `FixieClient` object and use it to
create a `Session` and send queries within the `Session`:

```
import fixie
client = fixie.FixieClient()
session = client.create_session()
response = session.query("What is 38 * 20302?")
print(response)
```


