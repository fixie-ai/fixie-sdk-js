import contextlib
import importlib
import os
import sys
from typing import Tuple

from fixieai import agents
from fixieai.agents import utils
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
    agent_impl = getattr(module, attr)
    utils.validate_code_shot_agent(agent_impl)
    return config, agent_impl


def uvicorn_app_factory():
    """Returns an app that can be used to serve an agent with uvicorn.

    The FIXIE_REFRESH_AGENT_ID environment variable can be set to trigger a refresh on startup.
    """
    _, impl = load_agent_from_path(".")
    return impl.app(os.getenv("FIXIE_REFRESH_AGENT_ID"))


if __name__ == "__main__":
    # Load the agent (typically within an agent-specific venv) to ensure the Python module can be loaded
    # without errors. See `fixie agent serve` and `fixie agent deploy --validate`.
    load_agent_from_path(".")
