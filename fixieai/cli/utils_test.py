import dataclasses
from typing import Optional

from . import utils


def test_yaml_formatting():
    @dataclasses.dataclass
    class C(utils.DataClassYamlMixin):
        string: str = "default value"
        optional: Optional[str] = None

    defaults = C()
    assert defaults.to_yaml() == "string: default value\n"

    with_optional = C(optional="optional value")
    assert (
        with_optional.to_yaml() == "string: default value\noptional: optional value\n"
    )

    multiline = C(string="line1\nline2\n", optional="optional value")
    assert (
        multiline.to_yaml() == "string: |\n  line1\n  line2\noptional: optional value\n"
    )
