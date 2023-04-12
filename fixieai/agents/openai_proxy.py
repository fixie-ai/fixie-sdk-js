import contextvars
import functools
import logging
import os
import sys

import wrapt
from starlette.middleware.base import BaseHTTPMiddleware

import fixieai.constants

FAKE_OPENAI_KEY = "sk-fixie-openai-key"

logger = logging.getLogger(__name__)
_auth_token = contextvars.ContextVar("openai_proxy.auth_token_ctx")


def enable_openai_proxy() -> bool:
    if "OPENAI_API_BASE" in os.environ or "OPENAI_API_KEY" in os.environ:
        logger.warning(
            "OpenAI proxy is not enabled; leave OPEN_API_BASE and OPENAI_API_KEY unset to use the Fixie OpenAI proxy."
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

            if (
                self.api_base == fixieai.constants.FIXIE_OPENAI_PROXY_URL
                and self.api_key == FAKE_OPENAI_KEY
            ):
                self.api_key = _auth_token.get()
                if self.api_key is None:
                    raise ValueError("The Fixie auth token contextvar was not set.")

        module.APIRequestor.__init__ = patched_init

    wrapt.register_post_import_hook(_patch_api_requestor, "openai.api_requestor")
    os.environ["OPENAI_API_BASE"] = fixieai.constants.FIXIE_OPENAI_PROXY_URL
    os.environ["OPENAI_API_KEY"] = FAKE_OPENAI_KEY

    return True


class AuthTokenForwarderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        BEARER_PREFIX = "Bearer "

        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith(BEARER_PREFIX):
            reset_token = _auth_token.set(authorization[len(BEARER_PREFIX) :])
            try:
                return await call_next(request)
            finally:
                _auth_token.reset(reset_token)
        else:
            return await call_next(request)
