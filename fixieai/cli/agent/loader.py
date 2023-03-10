import importlib
import os
import sys
from typing import Tuple

from fixieai import agents
from fixieai.cli.agent import agent_config


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

    module = importlib.import_module(module_name)
    return config, getattr(module, attr)
