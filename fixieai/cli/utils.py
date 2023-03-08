from typing import TextIO, Type, TypeVar, Union

import dataclasses_json
import yaml

A = TypeVar("A", bound="DataClassYamlMixin")


class DataClassYamlMixin(dataclasses_json.DataClassJsonMixin):
    @classmethod
    def from_yaml(cls: Type[A], config: Union[str, TextIO]) -> A:
        return cls.from_dict(yaml.safe_load(config))

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), sort_keys=False)  # type: ignore
