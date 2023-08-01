from __future__ import annotations

import contextlib
import dataclasses
import traceback

import fastapi
from fastapi.responses import JSONResponse

from fixieai.agents import api

UNHANDLED_EXCEPTION_RESPONSE_TEXT = (
    "I'm sorry, an error occurred while processing your request."
)


class AgentException(Exception):
    """An exception raised by an Agent."""

    def __init__(
        self,
        response_message: str,
        error_code: str,
        error_message: str,
        http_status_code: int = 500,
        **details,
    ):
        super().__init__(error_message)
        self._response_message = response_message
        self._http_status_code = http_status_code
        self._error_code = error_code
        self._error_message = error_message
        self._details = details

    def to_response(self) -> api.AgentResponse:
        """Converts the AgentException into an AgentResponse."""

        # Add exception details to the error details.
        error = api.AgentError(
            code=self._error_code,
            message=self._error_message,
            details={
                "traceback": traceback.format_exception(
                    type(self), self, self.__traceback__
                ),
                **self._details,
            },
        )

        return api.AgentResponse(
            api.Message(self._response_message),
            error=error,
        )

    @classmethod
    def fastapi_handler(cls, request: fastapi.Request, exc: AgentException):
        """A FastAPI exception handler for AgentExceptions."""
        return JSONResponse(
            dataclasses.asdict(exc.to_response()),
            status_code=exc._http_status_code,
        )

    @staticmethod
    @contextlib.contextmanager
    def exception_remapper():
        """Remaps unhandled exceptions into AgentExceptions."""
        try:
            yield
        except AgentException:
            raise
        except Exception as exc:
            raise AgentException(
                response_message=UNHANDLED_EXCEPTION_RESPONSE_TEXT,
                error_code="ERR_AGENT_UNHANDLED_EXCEPTION",
                error_message="An unhandled exception occurred while processing the request.",
                http_status_code=500,
            ) from exc
