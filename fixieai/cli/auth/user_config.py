import dataclasses
import os
from typing import List, Optional

from fixieai import constants
from fixieai.cli import utils


@dataclasses.dataclass
class EnvironmentSpecificKey(utils.DataClassYamlMixin):
    """Represents an API key bound to a specific environment."""

    url: str
    """The URL of the environment."""

    api_key: str
    """The API key for the environment."""


@dataclasses.dataclass
class UserConfig(utils.DataClassYamlMixin):
    """Represents user config at ~/.config/fixie/config.yaml"""

    fixie_api_key: Optional[str] = None
    """The default API key, will be used if no URL-specific key matches."""

    environment_api_keys: List[EnvironmentSpecificKey] = dataclasses.field(
        default_factory=lambda: [],
    )
    """Environment-specific API keys."""

    @property
    def api_key(self) -> Optional[str]:
        for environment_key in self.environment_api_keys:
            if environment_key.url == constants.FIXIE_API_URL:
                return environment_key.api_key

        # Otherwise return the default API key
        return self.fixie_api_key

    @api_key.setter
    def api_key(self, value: str):
        if self.api_key != value:
            # Append it to the url-specific keys and make it the default
            self.environment_api_keys.append(
                EnvironmentSpecificKey(constants.FIXIE_API_URL, value)
            )
            self.fixie_api_key = value


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
