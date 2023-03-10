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
    high, low = query.text.replace(" ", "").split(",")
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
`fixie serve` command, or (2) Deploy it to the Fixie platform using the `fixie deploy`
command. Using `fixie serve` allows you to debug the agent as it runs locally, but
is generally only advisable for initial development. 

```bash
$ fixie serve
```




To test an Agent locally, run it on your machine, and send it an HTTP GET request on
the port 8181. This will return the list of few-shot examples supported by the Agent,
demonstrating that the Agent is responding to queries on the correct port.

For example, to test the above agent, run the following command:

```bash
$ pip install fixieai
$ python examples/agents/random.py

# In another terminal...
$ curl http://localhost:8181 | python -m json.tool
```

You should see something like:
```
{
    "base_prompt": "I am a simple agent that generates a random number between two given values.",
    "few_shots": [
        "Q: Generate a random number between 0 and 19.\nAsk Func[genrand]: 0, 19\nFunc[genrand] says: 17\nA: The random number is 17.",
        "Q: Generate a random value from 5 to 10, inclusive.\nAsk Func[genrand]: 5, 10\nFunc[genrand] says: 8\nA: The random number is 8."
    ]
}
```

The Agent code itself will respond to a POST request sent to the URL `http://localhost:8181/genrand`
with a JSON payload containing the parameters to the `genrand` function. For example:

```bash
$ curl -X POST -H "Content-Type: application/json" \
  --data '{"message": {"text": "1, 100"}}' \
  http://localhost:8181/genrand
```

You should get back the result:
```json
{"message":{"text":"66","embeds":{}}}
```

The format of the JSON messages accepted by and returned by Fixie Agents is described in
the [Agent Protocol](agent-protocol.md) document.

## Deploy your Agent

You can deploy your Agent on any web server that supports Python. We recommend using [Replit](https://replit.com) as an easy-to-use
starting point.

All you need to do is create a new Python Replit project, and copy
the code for your Agent into the `main.py` file. You can then run the Agent by clicking the "Run" button in the Replit UI. Your Agent should
have a URL that you can use to test it. For example, if you named your Replit project `myrandagent`, you can test your Agent by running:

```bash
curl -X POST -H "Content-Type: application/json" \
   --data '{"message": {"text": "1, 100"}}' \
   https://myrandagent.repl.co:8181/genrand
```

## Integrate your Agent into Fixie

Now you're ready to create your Agent in the Fixie Platform.
Visit [https://app.fixie.ai/agents](https://app.fixie.ai/agents) and click on the "Add Agent" button. You'll be prompted to enter the URL
of your Agent, which in the Replit example above would be

```
https://myrandagent.repl.co:8181
```

The **Agent Handle** field should contain the same string used
in your Agent's `agent.serve()` call. In the example above, the Agent Handle is `randint`, however, since this handle might already
be taken by another Agent, you will need to change the Agent handle
in the `agent.serve()` call to something unique. (Once you've claimed
a handle, you can use it for future iterations of your Agent
code; it is not necessary to change the Agent handle every time you
update your Agent code.) 

Once you've added the Agent, you can test it out by entering
a Fixie Session and issuing a query such as:

```
@randint Generate a random number between 1 and 100.
```

Congrats! You've just created your first Fixie Agent!

See [Agent Protocol](agent-protocol.md) for details on how to implement an Agent directly
in a language other than Python, as well as [Agent API](agents.md) for details on the
complete Fixie Agent API.
