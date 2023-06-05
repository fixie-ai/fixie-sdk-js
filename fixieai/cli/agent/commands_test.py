import os
import pathlib
import queue
import random
import string
import threading
import time
import unittest.mock
from typing import Callable, Dict, Optional

import click.testing
import gql.client
import pytest
import validators

import fixieai
from fixieai import constants
from fixieai.cli import cli
from fixieai.cli.agent import agent_config

from . import commands


@pytest.fixture(autouse=True)
def mock_fixie_api_key(mocker):
    mocker.patch.object(constants, "fixie_api_key", return_value="TEST")
    os.environ["FIXIE_API_KEY"] = "TEST"


@pytest.fixture(autouse=True)
def mock_graphql(mocker):
    response_mocks: Dict[str, Callable] = {}

    def _execute(document, *args, **kwargs):
        mocked_queries = {
            "getUsername": {"user": {"username": "testuser"}},
            "getAgentById": {
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
            },
            "UpdateAgent": {
                "updateAgent": {
                    "agent": {
                        "agentId": "testuser/testagent",
                    }
                }
            },
            "SetCurrentAgentRevision": {
                "updateAgent": {
                    "agent": {
                        "agentId": "testuser/testagent",
                    }
                }
            },
            "CreateAgentRevision": {
                "createAgentRevision": {"revision": {"id": "FAKEID"}}
            },
            "GetSampleQueries": {
                "agentById": {"queries": ["Why did the chicken cross the road?"]}
            },
            "GetRevisionId": {"agentById": {"currentRevision": {"id": "FAKEID"}}},
            "DeleteRevision": {
                "deleteAgentRevision": {"agent": {"agentId": "testuser/testagent"}}
            },
        }

        operation = document.definitions[0].name.value
        if operation in response_mocks:
            return response_mocks[operation](document, *args, **kwargs)
        if operation in mocked_queries:
            return mocked_queries[operation]
        else:
            raise ValueError("Unmocked GraphQL operation: " + operation)

    mocker.patch.object(gql.client.Client, "execute", side_effect=_execute)
    return response_mocks


@pytest.fixture(autouse=True)
def mock_tunnel(mocker):
    tunnel = mocker.patch("fixieai.cli.agent.tunnel.Tunnel")
    tunnel.return_value.__enter__.return_value = ["mock://mock.example.com"]
    return tunnel


@pytest.fixture(autouse=True)
def mock_fixie_requirement(mocker):
    # Use the current version of fixieai as the fixie dependency.
    mocker.patch.object(
        commands,
        "CURRENT_FIXIE_REQUIREMENT",
        str(pathlib.Path(fixieai.__file__).parent.parent),
    )


@pytest.fixture()
def mock_server_process_ctx(mocker):
    mock_context_manager = unittest.mock.MagicMock()
    mock_context_manager.stop_queue = queue.Queue()

    def _server_process(console, event, *_, **__):
        mock_process = unittest.mock.MagicMock()
        mock_process.poll.return_value = None

        def _stop(code):
            mock_process.poll.return_value = code
            mock_process.returncode = code
            event.set()

        def _enter(*args, **kwargs):
            if mock_context_manager.stop_immediately == True:
                _stop(0)
            else:
                mock_context_manager.stop_queue.put(_stop)

            return mock_process

        mock_context_manager.__enter__.side_effect = _enter
        return mock_context_manager

    mocker.patch.object(commands, "_server_process", side_effect=_server_process)

    return mock_context_manager


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


def test_temporary_revision_replacer(mock_graphql):
    """Tests the _temporary_revision_replacer context manager."""

    mock_graphql["GetRevisionId"] = unittest.mock.MagicMock()
    mock_graphql["CreateAgentRevision"] = unittest.mock.MagicMock()
    mock_graphql["DeleteRevision"] = unittest.mock.MagicMock()
    mock_graphql["SetCurrentAgentRevision"] = unittest.mock.MagicMock()

    counter = 0

    def next_revision_id():
        nonlocal counter
        counter += 1
        return str(counter)

    mock_graphql["GetRevisionId"].side_effect = lambda *_, **__: {
        "agentById": {"currentRevision": {"id": str(counter)}}
    }
    mock_graphql["CreateAgentRevision"].side_effect = lambda *_, **__: {
        "createAgentRevision": {"revision": {"id": next_revision_id()}}
    }

    mock_console = unittest.mock.MagicMock()
    with commands._temporary_revision_replacer(
        mock_console, fixieai.FixieClient(), "testagent"
    ) as replacer:
        # The first replacement should create a new revision.
        assert mock_graphql["CreateAgentRevision"].call_count == 0
        replacer("mock://mock.example.org")
        assert (
            mock_graphql["CreateAgentRevision"].call_args[1]["variable_values"][
                "externalDeployment"
            ]["url"]
            == "mock://mock.example.org"
        )
        assert mock_graphql["DeleteRevision"].call_count == 0

        # The second replacement should create a new revision and delete the previously created revision.
        replacer("mock://mock2.example.org")
        assert (
            mock_graphql["CreateAgentRevision"].call_args[1]["variable_values"][
                "externalDeployment"
            ]["url"]
            == "mock://mock2.example.org"
        )
        assert (
            mock_graphql["DeleteRevision"].call_args[1]["variable_values"]["revisionId"]
            == "1"
        )

    # When the context manager exits it should delete the last temporary revision and restore the initial revision.
    assert (
        mock_graphql["DeleteRevision"].call_args[1]["variable_values"]["revisionId"]
        == "2"
    )
    assert (
        mock_graphql["SetCurrentAgentRevision"].call_args[1]["variable_values"][
            "currentRevisionId"
        ]
        == "0"
    )


def test_temporary_revision_replacer_no_current_revision(mock_graphql):
    """Tests the _temporary_revision_replacer context manager when there is no current revision."""

    mock_graphql["GetRevisionId"] = unittest.mock.MagicMock()
    mock_graphql["CreateAgentRevision"] = unittest.mock.MagicMock()
    mock_graphql["DeleteRevision"] = unittest.mock.MagicMock()
    mock_graphql["SetCurrentAgentRevision"] = unittest.mock.MagicMock()

    counter = 0

    def next_revision_id():
        nonlocal counter
        counter += 1
        return str(counter)

    mock_graphql["GetRevisionId"].return_value = {
        "agentById": {"currentRevision": None}
    }
    mock_graphql["CreateAgentRevision"].side_effect = lambda *_, **__: {
        "createAgentRevision": {"revision": {"id": next_revision_id()}}
    }

    mock_console = unittest.mock.MagicMock()
    with commands._temporary_revision_replacer(
        mock_console, fixieai.FixieClient(), "testagent"
    ) as replacer:
        assert mock_graphql["CreateAgentRevision"].call_count == 0
        replacer("mock://mock.example.org")
        assert (
            mock_graphql["CreateAgentRevision"].call_args[1]["variable_values"][
                "externalDeployment"
            ]["url"]
            == "mock://mock.example.org"
        )

    # Exiting the context manager should delete the last revision, but there's no revision to restore.
    assert (
        mock_graphql["DeleteRevision"].call_args[1]["variable_values"]["revisionId"]
        == "1"
    )
    assert mock_console["SetCurrentRevision"].call_count == 0


@pytest.mark.parametrize(
    "command",
    [
        ["agent", "serve"],
        ["agent", "serve", "foo/bar/baz"],
        ["agent", "deploy", "--no-validate"],
        ["agent", "deploy", "foo/bar/baz", "--no-validate"],
        # venv provisioning takes a long time, so only test it once per command.
        ["agent", "serve", "foo/bar/baz", "--venv"],
        ["agent", "deploy", "foo/bar/baz", "--validate"],
    ],
)
def test_implicit_init(mocker, command, mock_server_process_ctx):
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem():
        mock_server_process_ctx.stop_immediately = True

        result = runner.invoke(
            cli.fixie,
            command,
        )
        assert result.exit_code == 0, result.stdout


def test_fixie_serve_reload(mocker, mock_server_process_ctx):
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.fixie, ["agent", "init"])
        assert result.exit_code == 0, result.stdout

        # Wait a bit so that filesystem notifications from agent init don't appear as modifications.
        time.sleep(1)

        # Start the server.
        def _run_in_background():
            nonlocal result
            result = runner.invoke(cli.fixie, ["agent", "serve", "--reload"])

        background_thread = threading.Thread(target=_run_in_background, daemon=True)
        background_thread.start()

        # Wait for the server process to be "started".
        stop_server = mock_server_process_ctx.stop_queue.get(timeout=5.0)

        # It should not restart until we modify main.py.
        with pytest.raises(queue.Empty):
            _ = mock_server_process_ctx.stop_queue.get(timeout=0.5)

        # Modify `main.py` and we should see the process get restarted.
        pathlib.Path("main.py").touch()
        stop_server = mock_server_process_ctx.stop_queue.get(timeout=5.0)
        mock_server_process_ctx.__exit__.assert_called_once()

        # Simulate the server process ending.
        stop_server(0)
        background_thread.join()
        assert result.exit_code == 0, result.stdout


def test_fixie_serve_tunnel_rotate(mock_graphql, mock_server_process_ctx, mock_tunnel):
    # Mock the tunnel iterator with a blocking queue.
    tunnel_queue: Optional[queue.Queue] = queue.Queue()

    def _mock_tunnel_iter(*_, **__):
        while tunnel_queue:
            yield tunnel_queue.get()

    mock_tunnel.return_value.__enter__.side_effect = _mock_tunnel_iter

    # Mock revision creation
    mock_revisions_queue: queue.Queue = queue.Queue()

    def _mock_revision_creation(*args, **kwargs):
        mock_revisions_queue.put((args, kwargs))
        return {"createAgentRevision": {"revision": {"id": "FAKEID"}}}

    mock_graphql["CreateAgentRevision"] = _mock_revision_creation

    runner = click.testing.CliRunner()
    with runner.isolated_filesystem():
        result: Optional[click.testing.Result] = None

        # Start the server.
        def _run_in_background():
            nonlocal result
            result = runner.invoke(cli.fixie, ["agent", "serve"])
            assert result.exit_code == 0, result.stdout

        background_thread = threading.Thread(target=_run_in_background, daemon=True)
        background_thread.start()

        # Simulate the initial tunnel URL.
        assert tunnel_queue
        tunnel_queue.put("mock://tunnel1")

        # Wait for the initial revision to be created.
        (_, kwargs) = mock_revisions_queue.get(timeout=5.0)
        assert (
            kwargs["variable_values"]["externalDeployment"]["url"] == "mock://tunnel1"
        )

        # Rotate the tunnel and we should see a second revision created.
        assert tunnel_queue
        tunnel_queue.put("mock://tunnel2")
        (_, kwargs) = mock_revisions_queue.get(timeout=5.0)
        assert (
            kwargs["variable_values"]["externalDeployment"]["url"] == "mock://tunnel2"
        )

        # Simulate the server process ending.
        stop_server = mock_server_process_ctx.stop_queue.get(5.0)
        stop_server(0)

        # Close the mock tunnel.
        assert tunnel_queue
        tunnel_queue.put(None)
        tunnel_queue = None

        background_thread.join()
        assert result
        assert result.exit_code == 0, result.stdout
