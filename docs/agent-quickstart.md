# Fixie Agent Quickstart

Fixie allows you to extend the capabilities of the Fixie Platform by building your own **agents**, which are specialized software components that combine a set of **few-shot examples** with **code** to invoke external systems. We call this combination of few-shots coupled with code **Code Shots** (clever, eh?).

You can implement Fixie agents in any programming language. However, the Fixie SDK currently provides bindings only for Python. See the [Agent Protocol](agent-protocol.md) for details on implementing your own agent in a language other than Python. We'll be shipping bindings for other languages soon!

## Create a Fixie Agent

The first step is to create a new agent directory using the `fixie init` command:

```bash
$ mkdir myagent
$ cd myagent
$ fixie init
Handle [myagent]: 
Description []: A simple test agent.
Entry point [main:agent]: 
More info url []: 
```

`fixie init` will prompt you to enter some information about your agent.
* **Handle**: the unique identifier used to identify the agent in the Fixie Platform. 
* **Description**: an optional plain-text description of the agent's abilities.
* **Entry point**: the name of the Python module that contains the agent code, which we will create in the next step below.
* **More info url**: an optional URL that you can provide, which offers more information about the agent. This can point to any website. * **Public**: flag indicates whether the agent should be publicly visible in the Fixie Platform for other users. If you set this to `True`, anyone can use your agent in their own applications.

Running `fixie init` will create the file `agent.yaml` in the current directory, containing metadata on the agent.

## Write the Agent Code

Next, paste the following code into a file called `main.py`:

```python
import random
import fixieai

BASE_PROMPT = "I am a simple agent that generates a random number between two given values."
FEW_SHOTS = """
Q: Generate a random number between 0 and 19.
Ask Func[genrand]: 0, 19
Func[genrand] says: 17
A: The random number is 17.

Q: Generate a random value from 5 to 10, inclusive.
Ask Func[genrand]: 5, 10
Func[genrand] says: 8
A: The random number is 8.
"""

agent = fixieai.CodeShotAgent(BASE_PROMPT, FEW_SHOTS)

@agent.register_func()
def genrand(query: fixieai.Message) -> str:
    low, high = query.text.replace(" ", "").split(",")
    return str(random.randint(int(low), int(high)))
```

The code consists of two main parts:

* **`BASE_PROMPT`** and **`FEW_SHOTS`**: These are the few-shot examples that define the agent's purpose and behavior. The few-shots are used to provide examples to the underlying Large Language Model, such as GPT-4, as well as to provide the Fixie Platform information on what kinds of queries this agent can support.
* **Code snippets**: These are the functions that are invoked by the Code Shots. The code snippets are registered with the agent using the `register_func` decorator.

In the `FEW_SHOTS` string, the `Func[genrand]` keyword indicates that the function `genrand` should be invoked when the output of the underlying LLM starts with this string. The values following `Ask Func[genrand]:` are passed to the function as the `query.text` parameter. In this case, the function parses out the values and returns a random number between those two values.

## Test Your Agent

To test your agent, you have two options: 
1. Run it on your local machine using the `fixie agent serve` command
1. Deploy it to the Fixie platform using the `fixie agent deploy` command.

```bash
$ fixie serve
Opening tunnel to 0.0.0.0:8181...
Tunneling 0.0.0.0:8181 via https://df03e6d61a9f11.lhr.life
```

When running `fixie agent serve`, a tunnel is set up that allows the agent, running on your local machine, to be accessed from the Fixie Platform. The URL of the tunnel is printed on the console. If you quit the `fixie agent serve` process (e.g., by pressing Ctrl-C), the
tunnel is torn down and your agent is no longer accessible.

You can now use `fixie console` to send a message to your agent directly:

```bash
$ fixie console
Welcome to Fixie!
Connected to: https://app.fixie.ai/sessions/stormy-luxuriant-ferryboat
fixie 🦊❯ @myagent Generate a random number between 10 and 50
   @user: @mdw/myagent Generate a random number between 10 and 50
   @myagent: Generate a random number between 10 and 50
   @myagent: Ask Func: 10, 50
   @myagent: Func says: 48
   @myagent: The random number is 48.
1❯ The random number is 48.
```

In the `fixie agent serve` window, you should also see debugging output showing that your agent code was invoked with a `POST` request to the `/genrand` endpoint.

## Deploy Your Agent

Agents can be deployed on any web server that supports Python. Alternatively, you can deploy your agent directly to the Fixie platform, which will handle hosting the agent functions in the cloud.

To deploy your agent, simply run `fixie agent deploy`:

```bash
$ fixie agent deploy
✅ Deploying...
✅ Refreshing...
```

This process takes about a minute to complete. Once deployed, you can use your agent via the [Fixie Web UI](http://app.fixie.ai) or the `fixie console` tool.

## Agent REST API

Once deployed (via `fixie agent serve` or `fixie agent deploy`), your agent can also be invoked
via a REST API, using a `POST` request to the endpoint `/api/agent/<username>/<agent_handle>`.
For example, the `fixie/calc` agent can be invoked as follows:

```bash
$ export FIXIE_API_KEY=<Your Fixie API key>
$ curl https://app.fixie.ai/api/agents/fixie/calc \
  -H "Authorization: Bearer ${FIXIE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{ "message": {"text": "What is 999 + 222?" }}'
```

Your Fixie API key can be obtained from your user profile page.

## Fixie GraphQL API

Apart from the Agent REST API described above, the Fixie GraphQL API is a more rich and
powerful API surface for interacting with Fixie, including creating Agents, sending
messages, and more. For more information, see the
[Fixie GraphQL API documentation](https://app.fixie.ai/static/docs/index.html).

## Implementing Agents without Python

Refer to the [Agent Protocol](agent-protocol.md) documentation for details on implementing an agent in a language other than Python. For complete information on the Fixie Agent API, see [Agent API](agents.md).
