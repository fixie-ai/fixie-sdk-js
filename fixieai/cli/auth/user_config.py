import dataclasses
import os
from typing import List, Optional

import dataclasses_json

from fixieai import constants
from fixieai.cli import utils


@dataclasses.dataclass
class EnvironmentSpecificAuthToken(utils.DataClassYamlMixin):
    """Represents an auth token bound to a specific environment."""

    url: str
    """The URL of the environment."""

    auth_token: str
    """The auth token for the environment."""


@dataclasses.dataclass
class UserConfig(utils.DataClassYamlMixin):
    """Represents user config at ~/.config/fixie/config.yaml"""

    default_auth_token: Optional[str] = dataclasses.field(
        default=None, metadata=dataclasses_json.config(field_name="fixie_api_key")
    )
    """The default auth token, will be used if no URL-specific auth token matches."""

    environment_auth_tokens: List[EnvironmentSpecificAuthToken] = dataclasses.field(
        default_factory=lambda: [],
    )
    """Environment-specific auth tokens."""

    @property
    def auth_token(self) -> Optional[str]:
        for environment_key in self.environment_auth_tokens:
            if environment_key.url == constants.FIXIE_API_URL:
                return environment_key.auth_token

        # Otherwise return the default auth token
        return self.default_auth_token

    @auth_token.setter
    def auth_token(self, value: str):
        if self.auth_token != value:
            # Append it to the environment-specific tokens and make it the default
            self.environment_auth_tokens.append(
                EnvironmentSpecificAuthToken(constants.FIXIE_API_URL, value)
            )
            self.default_auth_token = value


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
