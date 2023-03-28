import dataclasses
from typing import Any, MutableMapping, TextIO, Type, TypeVar, Union

import dataclasses_json
import yaml

A = TypeVar("A", bound="DataClassYamlMixin")


class _NicelyFormattedYAMLString:
    """A string wrapper that formats multiline strings more nicely."""

    def __init__(self, value: str):
        self.value = value

    def dump(self, dumper: yaml.Dumper) -> yaml.Node:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", self.value, style="|" if "\n" in self.value else ""
        )


yaml.add_representer(
    _NicelyFormattedYAMLString,
    lambda dumper, value: value.dump(dumper),
)


class DataClassYamlMixin(dataclasses_json.DataClassJsonMixin):
    @classmethod
    def from_yaml(cls: Type[A], config: Union[str, TextIO]) -> A:
        return cls.from_dict(yaml.safe_load(config) or {})

    def to_yaml(self) -> str:
        as_dict: MutableMapping[str, Any] = self.to_dict()

        # Exclude any keys whose values and default values are None.
        for field in dataclasses.fields(self):
            if field.name not in as_dict:
                # Not all fields serialize to their Python names, leave them as-is.
                continue

            value = as_dict[field.name]
            if value is None and field.default is None:
                del as_dict[field.name]
            elif isinstance(value, str):
                as_dict[field.name] = _NicelyFormattedYAMLString(value)

        return yaml.dump(as_dict, sort_keys=False)  # type: ignore
