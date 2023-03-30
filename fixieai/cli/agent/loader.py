import contextlib
import functools
import importlib
import os
import sys
import threading
import time
from typing import Tuple

import dotenv

import fixieai
from fixieai import agents
from fixieai.cli.agent import agent_config


@contextlib.contextmanager
def _ensure_serving_disabled():
    original_serve = agents.AgentBase.serve

    def _fail(*_, **__):
        raise RuntimeError(
            "agent.serve() must not be called while your agent is being imported."
        )

    agents.AgentBase.serve = _fail  # type: ignore[assignment]
    try:
        yield
    finally:
        agents.AgentBase.serve = original_serve  # type: ignore[assignment]


def load_agent_from_path(
    path: str,
) -> Tuple[agent_config.AgentConfig, agents.AgentBase]:
    """Loads an Agent and its config from a path."""

    path = agent_config.normalize_path(path)
    config = agent_config.load_config(path)
    agent_dir = os.path.dirname(path) or "."

    dotenv_path = os.path.join(agent_dir, ".env")
    if os.path.exists(dotenv_path):
        dotenv.load_dotenv(dotenv_path)

    # Inject the agent directory into PYTHONPATH
    sys.path.insert(0, agent_dir)

    entry_point_parts = config.entry_point.split(":", 1)
    module_name = entry_point_parts[0]
    attr = entry_point_parts[1] if len(entry_point_parts) == 2 else "agent"

    with _ensure_serving_disabled():
        module = importlib.import_module(module_name)
    agent_impl = getattr(module, attr)
    assert isinstance(
        agent_impl, agents.AgentBase
    ), "Entrypoint must refer to an agent instance"
    agent_impl.validate()
    return config, agent_impl


def _refresh_agent_async(agent_handle: str):
    """Asynchronously pings Fixie to refresh the given agent_id."""

    def _refresh_agent_sync():
        # Pause a second to give the agent a moment to start up.
        time.sleep(1)
        fixieai.FixieClient().refresh_agent(agent_handle)

    thread = threading.Thread(target=_refresh_agent_sync, daemon=True)
    thread.start()


def uvicorn_app_factory():
    """Returns an app that can be used to serve an agent with uvicorn.

    If the FIXIE_REFRESH_ON_STARTUP environment variable is set to "true" an agent refresh
    will be triggered each time the agent starts up.
    """
    config, impl = load_agent_from_path(".")
    fastapi_app = impl.app()

    if os.getenv("FIXIE_REFRESH_ON_STARTUP") == "true":
        fastapi_app.add_event_handler(
            "startup", functools.partial(_refresh_agent_async, config.handle)
        )

    return fastapi_app


if __name__ == "__main__":
    # Load the agent (typically within an agent-specific venv) to ensure the Python module can be loaded
    # without errors. See `fixie agent serve` and `fixie agent deploy --validate`.
    load_agent_from_path(".")
