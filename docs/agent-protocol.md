# Fixie Agent Protocol

Fixie agents can be implemented in any programming language. The Fixie [Python Agent API](python-agent-api.md) provides a Python SDK that simplifies the implementation of agents in Python. However, it is possible to implement Fixie agents in any programming language, as long as the agent code conforms to the following protocol.

A Fixie agent is a program that accepts HTTP requests of two types:

* An HTTP `GET` request to the `/` endpoint, which returns a list of few-shot examples that the agent supports.
* An HTTP `POST` request to the `/FUNC` endpoint, which returns the result of calling the function `FUNC` with the parameters specified in the request. Agents can support multiple functions.

## Few-shot examples

Upon receiving an HTTP `GET` request to the `/` endpoint, the agent must return a list of few-shot examples that it supports. The few-shot examples are used to provide examples to the underlying Large Language Model, such as GPT-4, as well as to provide the Fixie Platform information on what kinds of queries this agent can support.

The few-shot examples are returned as a JSON object with the following format:

```json
{
  "base_prompt": "The base prompt for the few-shot examples.",
  "few_shots": [
    "The first few-shot example.",
    "The second few-shot example.",
    "The third few-shot example."
  ]
}
```

Each few-shot example consists of one or more lines, separated by a newline character (`\n`). The first line of each example must be a sample query, which must start with the prefix `Q: `. The final line of the few-shot example must be the corresponding answer, which must start with the prefix `A: `. The few-shot example may contain any number of lines in between the query and answer, representing intermediate outputs from the Large Language Model and responses to the LLM from external functions.

Here a single few-shot example:

```
Q: Generate a random number between 0 and 19.
Ask Func[genrand]: 0, 19
Func[genrand] says: 17
A: The random number is 17.
```

In this example, the first line represents a sample query that the agent can support. The second line is the LLM's response to receiving this query, which in this case indicates that the Function `genrand` should be invoked with the input string `0, 19`. The third line is the expected response from the Function `genrand`, and the final line is the answer to the query.

Using the Fixie Python SDK, the values of the `base_prompt` and `few_shots` fields are specified by setting the values of the `BASE_PROMPT` and `FEW_SHOTS` variables in the agent code, respectively.

## Function invocation

Upon receiving an HTTP `POST` request to the `/FUNC` endpoint, the agent must return the result of calling the agent function `FUNC` with the parameters specified in the body of the HTTP POST request.

The body of the POST request will be in the following format:

```json
{
  "message": {
    "text": "Argument to function call",
  }
}
```

The agent should invoke the function `FUNC`, passing in the contents of the JSON object `message` as the argument to the function call. The result of the function call should be returned as the value of the `result` field in the response to the HTTP POST request.

The response to the HTTP `POST` request should be a JSON object in the format:

```json
{
  "message": {
    "text": "Response to function call",
  }
}
```

Using the Fixie Python SDK, implementing an agent function is done using the `@fixieai.CodeShotAgent.register_func` decorator. The decorator takes a single argument, which is the function to be registered. The function must take a single argument, which contains the JSON `message` object from the HTTP POST request. The function should return a string, which will be the value of the `text` field in the response message returned by the agent.

See [python-agent-api.md](python-agent-api.md) for more information on the Fixie Python agent API, and [agent-quickstart.md](agent-quickstart.md) for a quickstart guide on how to implement agents in Fixie.