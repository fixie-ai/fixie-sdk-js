# Deploying LangChain Agents on Fixie

## Overview

[LangChain](https://python.langchain.com/) is a popular framework for developing applications built on top of Large Language Models. Fixie supports LangChain as a first-class citizen. This means you can develop LangChain Agents/Chains/Prompts just as you typically would and then quickly deploy them onto Fixie infrastructure.

## Why Deploy on Fixie?

Deploying on Fixie gives you three major advantages:

1. We host it for you (for free). Simply run `fixie deploy` and your Agent will be hosted in the cloud, complete with a REST API for calling it programatically and a shareable URL that will allow others to demo your agent in the browser.
1. No need for an OpenAI key. Fixie will automatically take care of that, and supports 1,000 free requests per day, per user. So if your creation gets popular, you're not stuck footing the bill or asking people to mint their own key.
1. It allows you to integrate with the rest of the Fixie ecosystem. This means other people in the community will be able to leverage your agent and vice-versa.

## Getting Started

First, you'll make to make sure you have installed the Fixie CLI and have authenticated to Fixie (these are necessary for deploying to Fixie):

1. Install Fixie on your machine: `pip install fixieai`
1. Create an account and link your command line to it: `fixie auth`

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

Now we need to tell Fixie about our Chain. To do this, run `fixie init`. Fixie will ask you a few questions about your agent like its handle (its name inside of Fixie) and description (this helps others understand how to use your creation).

The **most important part** is the `Entry Point`. This is where you tell Fixie where to find your function. The format is `name_of_your_python_file:name_of_your_function`.

In our case, our file is `main.py`, so we'll put `main:invoke_chain`.

Once you've done this, Fixie will create an `agent.yaml` file in the same directory. You can edit this any time.

You'll also notice that Fixie automatically created a `requirements.txt` file. If you're not familiar with `requirements.txt`, it's a simple way to define the module requirements for your project. Fixie will automatically install these on deploy. In our example, we need the following setup:

```python
# requirements.txt

langchain
openai
fixieai
```

Now we're ready to deploy! Run `fixie deploy` and Fixie takes care of the rest. Feel free to make changes and re-deploy.

When you're ready to make your agent **public** (so others can access it) simply change `published` to `true` in your `agent.yaml` file and run `fixie deploy` again.

## Developing and testing your Agent

When you're iteratively developing your agent, the fastest feedback loop is to run it locally, rather than re-deploying to Fixie on every change. To do this, run `fixie serve`. This will create a tunnel between your machine and Fixie, allowing you to test on Fixie but debug locally on your machine.

## Calling your Agent via API

Once your agent is deployed, Fixie automatically provides you with a REST API:

```console
curl "https://app.fixie.ai/api/agents/{username}/{agent_name}" \
  -d "{ 'message': {'text': 'colorful socks' }}" \
  -H "Authorization: Bearer {your_api_token}" \
  -H "Content-Type: application/json"
```

You can get your Fixie API Token from your [profile page](https://app.fixie.ai/profile).
