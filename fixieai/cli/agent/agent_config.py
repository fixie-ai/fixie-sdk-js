import dataclasses
import os
from typing import Optional

from fixieai.cli import utils


@dataclasses.dataclass
class AgentConfig(utils.DataClassYamlMixin):
    """Represents an agent.yaml config file."""

    handle: str
    name: Optional[str] = None
    description: str = ""
    more_info_url: str = ""
    entry_point: str = "main:agent"
    deployment_url: Optional[str] = None
    public: Optional[bool] = None


def normalize_path(path: Optional[str] = None) -> str:
    """Normalizes paths to an AgentConfig.

    Args:
        path: Optional path to either a directory or YAML file. If unspecified,
            will return "agent.yaml".
    """
    if not path:
        path = "agent.yaml"
    elif os.path.isdir(path):
        path = os.path.join(path, "agent.yaml")

    return path


def load_config(path: Optional[str] = None) -> AgentConfig:
    """Loads AgentConfig from the given path, or its default path.

    Args:
        path: Optional path to load config from. By default, config is loaded from
            "{cwd}/agent.yaml".
    """
    path = normalize_path(path)
    with open(path, "r") as fp:
        return AgentConfig.from_yaml(fp)


def save_config(agent_config: AgentConfig, path: Optional[str] = None):
    """Saves the given AgentConfig to the given path, or its default path.

    Args:
        agent_config: The AgentConfig object to save into file.
        path: Optional path to save. By default, it's saved to the default path at
            "{cwd}/agent.yaml".
    """
    path = normalize_path(path)
    with open(path, "w") as fp:
        fp.write(agent_config.to_yaml())
