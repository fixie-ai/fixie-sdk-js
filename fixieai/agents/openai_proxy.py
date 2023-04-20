import contextlib
import contextvars
import functools
import logging
import os
import sys
from typing import Iterable, Optional, Tuple

import starlette.types
import wrapt  # type: ignore

import fixieai.constants

FAKE_OPENAI_KEY = "sk-fixie-openai-key"

logger = logging.getLogger(__name__)

# A ContextVar that allows the current request token to be used for proxied OpenAI requests.
_current_request_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "openai_proxy.current_request_token",
    default=None,
)


def enable_openai_proxy() -> bool:
    """Enables the Fixie OpenAI proxy for outbound OpenAI requests made in the context of an agent request.

    Returns a value that indicates whether or not the proxy is enabled. If either OPENAI_API_BASE or
    OPENAI_API_KEY is already set, the proxy will not be enabled.

    The OpenAIProxyRequestTokenForwarderMiddleware must be used for the proxy to use valid auth tokens.
    """

    if "OPENAI_API_BASE" in os.environ or "OPENAI_API_KEY" in os.environ:
        logger.warning(
            "OpenAI proxy is not enabled; leave OPENAI_API_BASE and OPENAI_API_KEY unset to use the Fixie OpenAI proxy."
        )
        return False

    assert (
        "openai" not in sys.modules
    ), "OpenAI has already been loaded. The OpenAI proxy should be enabled before loading OpenAI."

    def _patch_api_requestor(module):
        original_init = module.APIRequestor.__init__

        @functools.wraps(original_init)
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)

            if self.api_base == fixieai.constants.FIXIE_OPENAI_PROXY_URL:
                if self.api_key != FAKE_OPENAI_KEY:
                    logger.warning(
                        "An OpenAI key was provided for the Fixie OpenAI proxy. "
                        "Ignoring it in favor of the current Fixie request token."
                    )

                self.api_key = _current_request_token.get()
                if self.api_key is None:
                    raise ValueError(
                        "The Fixie request token was not set. "
                        "The Fixie OpenAI proxy can only be used in the context of an agent request."
                    )
            elif self.api_key == FAKE_OPENAI_KEY:
                raise ValueError(
                    "The OpenAI base URL was changed but the key was not. "
                    "Leave the OpenAI base URL unspecified to use the Fixie OpenAI proxy or provide an OpenAI api key."
                )

        module.APIRequestor.__init__ = patched_init

    wrapt.register_post_import_hook(_patch_api_requestor, "openai.api_requestor")
    os.environ["OPENAI_API_BASE"] = fixieai.constants.FIXIE_OPENAI_PROXY_URL
    os.environ["OPENAI_API_KEY"] = FAKE_OPENAI_KEY

    return True


class OpenAIProxyRequestTokenForwarderMiddleware:
    """Middleware that allows the current request token to be used for proxied OpenAI requests."""

    def __init__(self, app: starlette.types.ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: starlette.types.Scope,
        receive: starlette.types.Receive,
        send: starlette.types.Send,
    ):
        BEARER_PREFIX = b"Bearer "

        with contextlib.ExitStack() as stack:
            http_headers: Iterable[Tuple[bytes, bytes]] = (
                scope["headers"] if scope["type"] in ("http", "websocket") else {}
            )

            # If there's a Bearer token in the headers, put it in the context var.
            for header, value in http_headers:
                if header.lower() == b"authorization" and value.startswith(
                    BEARER_PREFIX
                ):
                    reset_token = _current_request_token.set(
                        value[len(BEARER_PREFIX) :].decode()
                    )
                    stack.callback(lambda: _current_request_token.reset(reset_token))
                    break

            await self.app(scope, receive, send)
