import dataclasses
import os
from typing import Optional

from fixieai.cli import utils


@dataclasses.dataclass
class UserConfig(utils.DataClassYamlMixin):
    """Represents user config at ~/.config/fixie/config.yaml"""

    fixie_api_key: Optional[str] = None


def load_config(path: Optional[str] = None) -> UserConfig:
    """Loads UserConfig from the given path, or its default path.

    Args:
        path: Optional path to load config from. By default, config is loaded from
            "~/.config/fixie/config.yaml".
    """
    if path is None:
        path = os.path.expanduser("~/.config/fixie/config.yaml")
    with open(path, "r") as fp:
        return UserConfig.from_yaml(fp)


def save_config(user_config: UserConfig, path: Optional[str] = None):
    """Saves the given AgentConfig to the given path, or its default path.

    Args:
        user_config: The UserConfig object to save into file.
        path: Optional path to save. By default, it's saved to the default path at
            "~/.config/fixie/config.yaml".
    """
    if path is None:
        path = os.path.expanduser("~/.config/fixie/config.yaml")
        os.makedirs(os.path.expanduser("~/.config/fixie"), exist_ok=True)
    with open(path, "w") as fp:
        fp.write(user_config.to_yaml())
