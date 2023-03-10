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
pip install fixieai
```

Once installed, run `fixie auth` to authenticate with Fixie and start building.

## Build Agents

Agents are at the heart of the Fixie ecosystem, and we make it easy to build and contribute your own. To get started, check out our [examples repo](https://github.com/fixie-ai/fixie-examples) or [read the docs](https://docs.fixie.ai/agents/).

## Using the Fixie CLI

The Fixie CLI tool lets you use Fixie interactively from the command line.

Run `fixie --help` to see a list of available commands.

```
$ fixie console
Welcome to Fixie!
Connected to: https://app.fixie.ai/sessions/spark-typical-hardware
fixie 🚲❯  What's the price of Nvidia?
   @user: What's the price of Nvidia?
   @fixie: What's the price of Nvidia?
   @fixie: Thought: This is an atomic task.
   @fixie: Ask Agent: What's the price of Nvidia?
   @router: What's the price of Nvidia?
   @router: justin/stock
   @stock: What's the price of Nvidia?
   @stock: Thought: I need to get a stock quote for NVDA.
   @stock: Ask Func: NVDA
   @stock: Func says: $234.36 -3.45%
   @stock: The current share price for Nvidia is $234.36, down 3.45% today.
   @fixie: Agent says: The current share price for Nvidia is $234.36, down 3.45% today.
   @fixie: Thought: I need to repeat back this information.
   @fixie: The current share price for Nvidia is $234.36, down 3.45% today.
6❯ The current share price for Nvidia is $234.36, down 3.45% today.
```

## Integrate with our Client API

The simplest way to use Fixie from your app is to use the `fixie.query` method
to send a query:

```
import fixieai
response = fixieai.query("Hello there!")
print(response)
```

For more control, you can also create a `FixieClient` object and use it to
create a `Session` and send queries within the `Session`:

```
import fixieai
client = fixieai.FixieClient()
session = client.create_session()
response = session.query("What is 38 * 20302?")
print(response)
```
