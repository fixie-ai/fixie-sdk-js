from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import List, Union

import fastapi
import uvicorn
from pydantic import dataclasses as pydantic_dataclasses

from fixie.agents import utils
from fixie.agents.api import AgentQuery
from fixie.agents.api import AgentResponse
from fixie.agents.api import Message


@pydantic_dataclasses.dataclass
class AgentMetadata:
    """Metadata for a Fixie CodeShot Agent.

    This will get sent to the Fixie upon handshake.
    """

    agent_id: str
    base_prompt: str
    few_shots: List[str]

    def __post_init__(self):
        utils.strip_prompt_lines(self)
        utils.validate_code_shot_agent(self)


class CodeShotAgent(ABC):
    """Abstract CodeShot agent.

    To make a CodeShot agent, simply subclass and set the abstract fields:

        class CustomAgent(CodeShotAgent):
            handle = "fixie-agent-id"
            BASE_PROMPT = "A summary of what this agent does; how it does it; and its
                           personality"
            FEW_SHOTS = [
                # List of few_shots go here.
            ]

    Your agent may define as many or little python functions that will be accessible by
    the few_shots. Each python function should have the following syntax:

        def my_func(self, query: AgentQuery) -> ReturnType:
            ...

        , where ReturnType is one of `str`, `Message` or `AgentResponse`.

    These python functions can be used in the fewshot like:
        "Ask Func[my_func]: The query to send to the function"
        "Func[my_func] says: The output of the function back"

    """

    def __init__(self) -> None:
        # Call all abstract fields and lock the values in.
        self._agent_metadata: AgentMetadata = AgentMetadata(
            agent_id=self.agent_id,
            base_prompt=self.BASE_PROMPT,
            few_shots=self.FEW_SHOTS,
        )

    @property
    @abstractmethod
    def agent_id(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def BASE_PROMPT(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def FEW_SHOTS(self) -> List[str]:
        raise NotImplementedError()

    def serve(self, host: str = "0.0.0.0", port: int = 8181):
        """Starts serving the current agent at `{host}:{port}` via uvicorn.

        Args:
            host: The address to start listening at.
            port: The port number to start listening at.
        """
        fast_api = fastapi.FastAPI()
        fast_api.include_router(self.api_router())
        uvicorn.run(fast_api, host=host, port=port)

    def api_router(self) -> fastapi.APIRouter:
        """Returns a fastapi.APIRouter object that serves the agent."""
        router = fastapi.APIRouter()
        router.add_api_route("/", self._handshake, methods=["GET"])
        router.add_api_route("/{func_name}", self._serve_func, methods=["POST"])
        return router

    def _handshake(self) -> AgentMetadata:
        return self._agent_metadata

    def _serve_func(self, func_name: str, query: AgentQuery) -> AgentResponse:
        try:
            pyfunc = utils.get_pyfunc(self, func_name)
        except AttributeError:
            raise fastapi.HTTPException(
                status_code=404, detail=f"Func[{func_name}] doesn't exist"
            )
        except (ValueError, TypeError):
            raise fastapi.HTTPException(
                status_code=403, detail=f"Func[{func_name}] is not callable by api."
            )
        output = pyfunc(query)
        try:
            return _wrap_with_agent_response(output)
        except TypeError:
            raise TypeError(
                f"Func[{func_name}] returned unexpected output of type {type(output)}."
            )


def _wrap_with_agent_response(
    value: Union[str, Message, AgentResponse]
) -> AgentResponse:
    if isinstance(value, str):
        return AgentResponse(Message(value))
    elif isinstance(value, Message):
        return AgentResponse(value)
    elif isinstance(value, AgentResponse):
        return value
    else:
        raise TypeError(f"Unexpected type to wrap: {type(value)}")
