# Fixie Agent Quickstart

Fixie allows you to extend the capabilities of the Fixie Platform by building your own
**Agents**, which are specialized software components that combine a set of **few-shot examples**
with **code** to invoke external systems. We call this combination of few-shots coupled with code 
**Code Shots** (clever, eh?).

You can implement Fixie Agents in any programming language, however, the Fixie SDK currently
provides bindings only for Python. See the [Agent Protocol](agent-protocol.md) for details
on implementing your own Agent in a language other than Python. We'll be shipping bindings for
other languages soon!

## Create a Fixie Agent

The first step is to create a new Agent directory using the `fixie init` command:

```bash
$ mkdir myagent
$ cd myagent
$ fixie init
Handle [myagent]: 
Description []: A simple test agent.
Entry point [main:agent]: 
More info url []: 
Public [False]: 
```

`fixie init` will prompt you to enter some information about your Agent. The Agent **Handle**
is its unique identifier, and is used to identify the Agent in the Fixie Platform. 
The **Description** is an optional plain-text description of the Agent's abilities.
The **Entry point** is the name of the Python module that contains the Agent code, which
we will create in the next step below. The **More info url** is an optional URL that
you can provide that provides more information about the Agent; this can point to any website.
The **Public** flag indicates whether the Agent should be publicly visible in the Fixie
Platform for other users. If you set this to `True`, then anyone can use your Agent in their own applications.

Running `fixie init` will create the file `agent.yaml` in the current directory, containing
metadata on the Agent.

## Write the Agent code

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

* **`BASE_PROMPT`** and **`FEW_SHOTS`**: These are the few-shot examples that define the Agent's
  purpose and behavior. The few-shots are used to providing examples to the underlying
  Large Language Model, such as GPT-3, as well as to provide the Fixie Platform information
  on what kinds of queries this Agent can support.
* **Code snippets**: These are the functions that are invoked by the Code Shots. The
  code snippets are registered with the agent using the `register_func` decorator.

In the `FEW_SHOTS` string, the `Func[genrand]` keyword indicates that the function
`genrand` should be invoked when the output of the underlying LLM starts with this string.
The values following `Ask Func[genrand]:` are passed to the function as the `query.text`
parameter. In this case, the function parses out the values and returns a random number
between those two values.

## Test your Agent

To test your Agent, you have two options: (1) Run it on your local machine using the
`fixie agent serve` command, or (2) Deploy it to the Fixie platform using the
`fixie agent deploy` command. Using `fixie agent serve` allows you to debug the agent as
it runs locally, but is generally only advisable for initial development. 

```bash
$ fixie serve
Opening tunnel to 0.0.0.0:8181...
Tunneling 0.0.0.0:8181 via https://df03e6d61a9f11.lhr.life
```

When running `fixie agent serve`, a tunnel is set up that allows the Agent, running on your
local machine, to be accessed from the Fixie Platform. The URL of the tunnel is printed
on the console. If you quit the `fixie agent serve` process (e.g., by pressing Ctrl-C), the
tunnel is torn down and your Agent is no longer accessible.

Now you can use `fixie console` to send a message to your Agent directly:

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

In the `fixie agent serve` window, you should also see debugging output showing that your
Agent code was invoked with a `POST` request to the `/genrand` endpoint.

## Deploy your Agent

Agents can be deployed on any web server that supports Python, however, you can also
deploy your Agent directly to the Fixie platform, which takes care of hosting the Agent
functions in the cloud.

For this, all you need to do is run `fixie agent deploy`:

```bash
$ fixie agent deploy
✅ Deploying...
✅ Refreshing...
```

This will take about a minute to run. Once deployed, you can use your Agent via the Fixie web UI
or the `fixie console` tool.

## Implementing Agents without Python

See [Agent Protocol](agent-protocol.md) for details on how to implement an Agent directly
in a language other than Python, as well as [Agent API](agents.md) for details on the
complete Fixie Agent API.
