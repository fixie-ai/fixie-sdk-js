import dataclasses
import os
import yaml
from typing import Any, Callable, Optional, TextIO, Type, Union

import dataclasses_json
import prompt_toolkit

from fixieai.cli import validators


@dataclasses.dataclass
class AgentConfig(dataclasses_json.DataClassJsonMixin):
    """Represents an agent.yaml config file."""
    agent_id: str = "agent_id"
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
        return yaml.dump(self.to_dict(), sort_keys=False)


def load_config(path: Optional[str] = None) -> "AgentConfig":
    """Loads AgentConfig from the given path, or its default path.

    If config doesn't exist at path, a default config is returned.

    Args:
        path: Optional path to load config from. By default, config is loaded from
            "{cwd}/agent.yaml".
    """
    if path is None:
        path = os.path.join(os.getcwd(), "agent.yaml")
    try:
        with open(path, "r") as fp:
            return AgentConfig.from_yaml(fp)
    except FileNotFoundError:
        return AgentConfig()


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


def prompt_user(agent_config: AgentConfig):
    """Prompts the to edit values in AgentConfig."""
    print("""This utility will walk you through creating an agent.yaml file.
    
""")
    agent_config.agent_id = _prompt_user_for_str(
        "agent id",
        agent_config.agent_id,
        validators.validate_agent_id
    )
    agent_config.description = _prompt_user_for_str(
        "description",
        agent_config.description,
    )
    agent_config.entry_point = _prompt_user_for_str(
        "entry point",
        agent_config.entry_point,
    )
    agent_config.more_info_url = _prompt_user_for_str(
        "more info url",
        agent_config.more_info_url,
        validators.validate_url,
    )
    agent_config.public = _prompt_user_for_bool(
        "public?",
        agent_config.public,
    )


def _prompt_user_for_str(
    description: str,
    current_value: str,
    validator: Optional[Callable] = None
) -> str:
    while True:
        if current_value:
            prompt = f"{description}: ({current_value}) "
        else:
            prompt = f"{description}: "

        response = prompt_toolkit.prompt(prompt)
        if not response:
            response = current_value

        if validator:
            try:
                validator(response)
            except ValueError as e:
                print(e.args[0])
                continue
        break
    return response


def _prompt_user_for_bool(
    description: str,
    current_value: bool,
) -> bool:
    while True:
        if current_value:
            prompt = f"{description}: (Yes) "
        else:
            prompt = f"{description}: (No) "

        response = prompt_toolkit.prompt(prompt)
        response = response.strip()
        if not response:
            response = current_value
        elif response.lower() in ("y", "yes"):
            response = True
        elif response.lower() in ("n", "no"):
            response = False
        else:
            print("Please only type Yes or No.")
            continue
        break
    return response
