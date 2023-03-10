import contextlib
import importlib
import os
import sys
from typing import Tuple

from fixieai import agents
from fixieai.cli.agent import agent_config


@contextlib.contextmanager
def _ensure_serving_disabled():
    original_serve = agents.CodeShotAgent.serve

    def _fail(*_, **__):
        raise RuntimeError(
            "agent.serve() must not be called while your agent is being imported."
        )

    agents.CodeShotAgent.serve = _fail  # type: ignore[assignment]
    try:
        yield
    finally:
        agents.CodeShotAgent.serve = original_serve  # type: ignore[assignment]


def load_agent_from_path(
    path: str,
) -> Tuple[agent_config.AgentConfig, agents.CodeShotAgent]:
    """Loads an Agent and its config from a path."""

    path = agent_config.normalize_path(path)
    config = agent_config.load_config(path)
    agent_dir = os.path.dirname(path)

    # Inject the agent directory into PYTHONPATH
    sys.path.insert(0, agent_dir)

    entry_point_parts = config.entry_point.split(":", 1)
    module_name = entry_point_parts[0]
    attr = entry_point_parts[1] if len(entry_point_parts) == 2 else "agent"

    with _ensure_serving_disabled():
        module = importlib.import_module(module_name)
    return config, getattr(module, attr)


def uvicorn_app_factory():
    """Returns an app that can be used to serve an agent with uvicorn.

    The FIXIE_AGENT_PATH environment variable should be set if agent.yaml is not in the current directory.
    The FIXIE_REFRESH_AGENT_ID environment variable can be set to trigger a refresh on startup.
    """
    _, impl = load_agent_from_path(os.getenv("FIXIE_AGENT_PATH", "."))
    return impl.app(os.getenv("FIXIE_REFRESH_AGENT_ID"))
