import dataclasses
import os
import re
from typing import Optional, TextIO, Union

import dataclasses_json
import yaml


def _current_dirname() -> str:
    """Returns current directory name."""
    return _slugify(os.path.basename(os.getcwd()))


@dataclasses.dataclass
class AgentConfig(dataclasses_json.DataClassJsonMixin):
    """Represents an agent.yaml config file."""

    handle: str = dataclasses.field(default_factory=_current_dirname)
    name: str = ""
    description: str = ""
    entry_point: str = "main.py"
    more_info_url: str = ""
    deployment_url: str = ""
    public: bool = False

    @classmethod
    def from_yaml(cls, config: Union[str, TextIO]) -> "AgentConfig":
        """Loads AgentConfig from stream or string of yaml config."""
        return AgentConfig.from_dict(yaml.safe_load(config))

    def to_yaml(self) -> str:
        """Dumps AgentConfig as a yaml config."""
        return yaml.dump(self.to_dict(), sort_keys=False)  # type: ignore


def load_config(path: Optional[str] = None) -> "AgentConfig":
    """Loads AgentConfig from the given path, or its default path.

    Args:
        path: Optional path to load config from. By default, config is loaded from
            "{cwd}/agent.yaml".
    """
    if path is None:
        path = os.path.join(os.getcwd(), "agent.yaml")
    with open(path, "r") as fp:
        return AgentConfig.from_yaml(fp)


def save_config(agent_config: AgentConfig, path: Optional[str] = None):
    """Saves the given AgentConfig to the given path, or its default path.

    Args:
        agent_config: The AgentConfig object to save into file.
        path: Optional path to save. By default, it's saved to the default path at
            "{cwd}/agent.yaml".
    """
    if path is None:
        path = os.path.join(os.getcwd(), "agent.yaml")
    with open(path, "w") as fp:
        fp.write(agent_config.to_yaml())


def _slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = s.strip("-")
    return s
