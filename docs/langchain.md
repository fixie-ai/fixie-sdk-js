# Deploying LangChain Agents on Fixie

## Overview

[LangChain](https://python.langchain.com/) is a popular framework for developing applications built on top of Large Language Models. Fixie supports LangChain as a first-class citizen. This means you can develop LangChain Agents/Chains/Prompts just as you typically would and then quickly deploy them onto Fixie infrastructure.

## Why Deploy on Fixie?

Deploying on Fixie gives you three major advantages:

1. We host it for you (for free). Simply run `fixie deploy` and your Agent will be hosted in the cloud, complete with a REST API for calling it programatically and a shareable URL that will allow others to test your agent themselves.
1. No need for an OpenAI key. Fixie will automatically take care of that, and supports 1,000 free requests per day, per user. So if your creation gets popular, you're not stuck footing the bill or asking people to mint their own key.
1. It allows you to integrate with the rest of the Fixie ecosystem. This means other people in the community will be able to leverage your agent and vice-versa.

## Getting Started

First, you'll need to make sure you have `fixie` installed on your machine with `pip install fixieai`. This will install the Fixie CLI, which you'll need for deploying to Fixie.

Next, you'll need to tell Fixie what function to call to invoke your app. As an example, let's imagine something as simple as a [PromptTemplate](https://python.langchain.com/en/latest/getting_started/getting_started.html):

```python
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.chains import LLMChain

llm = OpenAI(temperature=0.9)
prompt = PromptTemplate(
    input_variables=["product"],
    template="What is a good name for a company that makes {product}?",
)
chain = LLMChain(llm=llm, prompt=prompt)
chain.run("colorful socks")
```

In the above example, we're calling `chain.run()` directly inside of our code with a hardcoded value of "colorful socks". This isn't that useful, since it means we can only get company names for colorful socks! Instead, we want a user to be able to provide the variable themselves, and we want Fixie to pass that to us.

To accomplish this, we're going to wrap `chain.run()` inside of a func. Here's our new version:

```python
# main.py

from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.chains import LLMChain

llm = OpenAI(temperature=0.9)
prompt = PromptTemplate(
    input_variables=["product"],
    template="What is a good name for a company that makes {product}?",
)
chain = LLMChain(llm=llm, prompt=prompt)

def invoke_chain(input):
  return chain.run(input)
```

Instead of calling `chain.run()` directly, we've instead wrapped it inside of a function called `invoke_chain` that takes a single `str` as an input variable. We then pass that string directly to our `chain.run()`.

Now we need to tell Fixie about our Chain. To do this, run `fixie init`. Fixie will ask you a few questions about your agent like its handle (it's "name" inside of Fixie) and description (this helps others understand how to use your creation).

The **most important part** is the `Entry Point`. This is where you tell Fixie where to find your function. The format is `name_of_your_python_file:name_of_your_function`.

In our case, our file is `main.py`, so we'll put `main.py:invoke_chain`.

Once you've done this, Fixie will create an `agent.yaml` file in the same directory. You can edit this anytime.

You'll also notice that Fixie automatically created a `requirements.txt` file. If you're not familiar with `reuirements.txt`, it's a simple way to define the module requirements for your project. Fixie will automatically install these on deploy. In our example, we need the following setup:

```python
# requirements.txt

langchain
openai
fixieai
```

Now we're ready to deploy! Run `fixie deploy` and Fixie takes care of the rest. Feel free to make changes and re-deploy.

When you're ready to make your agent Public (so others can access it) simply change `published` to `true` in your `agent.yaml` file and run `fixie deploy` again.

## Calling your Agent via API

Once your agent is deployed, Fixie automatically provides you with a REST API:

```console
curl "https://app.fixie.ai/api/agents/{username}/{agent_name}" \
  -d "{ 'message': {'text': 'colorful socks' }}" \
  -H "Authorization: Bearer {your_token}" \
  -H "Content-Type: application/json"
```

## Testing your agent locally

Before deploying you can test your agent locally by running `fixie serve`. This will create a tunnel between your machine and Fixie.

This is the best way to debug locally.
