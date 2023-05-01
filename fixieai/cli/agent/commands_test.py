import os
import pathlib
import random
import string
import subprocess
from unittest import mock

import click.testing
import gql.client
import pytest
import validators

import fixieai
from fixieai import constants
from fixieai.cli import cli
from fixieai.cli.agent import agent_config
from fixieai.client.client import FixieClient

from . import commands


@pytest.fixture(autouse=True)
def mock_fixie_api_key(mocker):
    mocker.patch.object(constants, "fixie_api_key", return_value="TEST")
    os.environ["FIXIE_API_KEY"] = "TEST"


@pytest.fixture(autouse=True)
def mock_graphql(mocker):
    def _execute(document, *args, **kwargs):
        if document.definitions[0].name.value == "getUsername":
            return {"user": {"username": "testuser"}}
        elif document.definitions[0].name.value == "getAgentById":
            return {
                "agentById": {
                    "agentId": "testuser/testagent",
                    "handle": "testagent",
                    "name": "Test Agent",
                    "description": "Test agent description",
                    "queries": [],
                    "funcUrl": "https://example.com",
                    "moreInfoUrl": "https://example.com",
                    "published": False,
                    "owner": {
                        "username": "testuser",
                    },
                }
            }
        elif document.definitions[0].name.value == "UpdateAgent":
            return {
                "updateAgent": {
                    "agent": {
                        "agentId": "testuser/testagent",
                    }
                }
            }
        else:
            raise ValueError(
                "Unmocked GraphQL operation: " + document.definitions[0].name.value
            )

    return mocker.patch.object(gql.client.Client, "execute", side_effect=_execute)


def test_update_agent_requirements_adds_fixie():
    new_requirements = commands._update_agent_requirements([], [])
    assert new_requirements == [commands.CURRENT_FIXIE_REQUIREMENT]


def test_update_agent_requirements_honors_specified_fixie():
    new_requirements = commands._update_agent_requirements([], ["fixieai"])
    assert new_requirements == ["fixieai"]


def test_update_agent_requirements_overrides_existing_fixie():
    new_requirements = commands._update_agent_requirements(
        ["fixieai", "fixieai == 0.0"], []
    )
    assert new_requirements == [commands.CURRENT_FIXIE_REQUIREMENT]


def test_update_agent_requirements_combines():
    new_requirements = commands._update_agent_requirements(
        ["package1", "package2"], ["package2", "package3"]
    )
    assert new_requirements == [
        "package1",
        "package2",
        commands.CURRENT_FIXIE_REQUIREMENT,
        "package3",
    ]


@pytest.mark.parametrize("seed", range(100))
def test_slugify(seed):
    random.seed(seed)

    text = "".join(random.choices(string.ascii_letters, k=40))
    slugified = commands._slugify(text)
    assert len(slugified) <= len(text)
    assert validators.slug(slugified)


def test_init():
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        result = runner.invoke(commands.init_agent)
        assert result.exit_code == 0

        config = agent_config.load_config(temp_dir)
        assert config.handle == commands._slugify(os.path.basename(temp_dir))
        assert os.path.exists(os.path.join(temp_dir, "main.py"))
        assert os.path.exists(os.path.join(temp_dir, "requirements.txt"))


def test_init_with_path():
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        result = runner.invoke(commands.init_agent, ["foo/bar/baz"])
        assert result.exit_code == 0

        agent_dir = os.path.join(temp_dir, "foo/bar/baz")
        config = agent_config.load_config(agent_dir)
        assert config.handle == "baz"
        assert os.path.exists(os.path.join(agent_dir, "main.py"))
        assert os.path.exists(os.path.join(agent_dir, "requirements.txt"))


def test_init_args():
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        result = runner.invoke(
            commands.init_agent,
            [
                "foo",
                "--handle",
                "my-handle",
                "--description",
                "a description",
                "--entry-point",
                "main:entrypoint",
                "--more-info-url",
                "https://example.com",
            ],
        )
        assert result.exit_code == 0
        agent_dir = os.path.join(temp_dir, "foo")
        config = agent_config.load_config(agent_dir)
        assert config.handle == "my-handle"
        assert config.description == "a description"
        assert config.entry_point == "main:entrypoint"
        assert config.more_info_url == "https://example.com"


def test_init_validation_prompting():
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        result = runner.invoke(
            commands.init_agent,
            ["foo"],
            input="""my invalid handle
my-handle
a description
invalid entry point
main:entrypoint
invalid URL

""",
        )
        assert result.exit_code == 0
        agent_dir = os.path.join(temp_dir, "foo")
        config = agent_config.load_config(agent_dir)
        assert config.handle == "my-handle"
        assert config.description == "a description"
        assert config.entry_point == "main:entrypoint"
        assert config.more_info_url == ""


@pytest.mark.parametrize(
    "command",
    [
        ["agent", "serve", "--no-tunnel"],
        ["agent", "serve", "foo/bar/baz", "--no-tunnel"],
        ["agent", "deploy", "--no-validate"],
        ["agent", "deploy", "foo/bar/baz", "--no-validate"],
        # venv provisioning takes a long time, so only test it once per command.
        ["agent", "serve", "foo/bar/baz", "--no-tunnel", "--venv"],
        ["agent", "deploy", "foo/bar/baz", "--validate"],
    ],
)
def test_implicit_init(mocker, command):
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem():
        subprocess_run = subprocess.run

        def mock_subprocess(cmd_args, *args, **kwargs):
            if "uvicorn" in cmd_args:
                # Mock out the uvicorn process.
                return mock.MagicMock()

            return subprocess_run(cmd_args, *args, **kwargs)

        mocker.patch.object(subprocess, "run", side_effect=mock_subprocess)

        # Use the current version of fixieai as the fixie dependency.
        mocker.patch.object(
            commands,
            "CURRENT_FIXIE_REQUIREMENT",
            str(pathlib.Path(fixieai.__file__).parent.parent),
        )

        # Mock out deployment API calls.
        mocker.patch.object(FixieClient, "deploy_agent", return_value=None)
        mocker.patch.object(FixieClient, "refresh_agent", return_value=None)

        result = runner.invoke(
            cli.fixie,
            command,
        )
        assert result.exit_code == 0
