# Llama Labs SDK

This is the official Python SDK for Llama Labs.

## What is Llama Labs?

Llama Labs is a platform for building applications using large language models. In Fixie, an application
consists of a set of natural-language **queries** that are handled by one or more **agents**.
Each agent consists of a large language model coupled with some custom code to process or generate
data, or call out to external systems, such as databases or APIs. By composing agents together,
you can create complex workflows with very little code.

## Installation

The easiest way to install the Llama Labs SDK is via `pip`:
```
pip install llamalabs
```

## Usage

The Llama Labs SDK provides a single class, `LlamaLabsClient`, which is used to communicate with the Llama Labs
API. To create a client, you need to provide your API key, which you can find in the Llama Labs
web application, on your profile page. Set the value of the `LLAMALABS_API_KEY` environment variable
to your API key, and then create a client as follows:
```
from llamalabs import LlamaLabsClient
client = LlamaLabsClient()
```




