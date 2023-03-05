import random
import string

import pytest
import validators

from fixieai.cli.agent import agent_config


@pytest.mark.parametrize("seed", range(100))
def test_slugify(seed):
    random.seed(seed)

    text = "".join(random.choices(string.ascii_letters, k=40))
    slugified = agent_config._slugify(text)
    assert len(slugified) <= len(text)
    assert validators.slug(slugified)
