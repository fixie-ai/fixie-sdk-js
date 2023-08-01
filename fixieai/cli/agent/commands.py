import contextlib
import functools
import io
import json
import os
import pathlib
import random
import re
import shlex
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
import venv
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

import click
import rich.console as rich_console
import rich.table
import validators
import watchfiles
from gql import gql

import fixieai.client
from fixieai import constants
from fixieai.cli.agent import agent_config
from fixieai.cli.agent import tunnel

# Regex pattern to match valid entry points: "module:object"
VAR_NAME_RE = r"(?![0-9])\w+"
ENTRY_POINT_PATTERN = re.compile(rf"^{VAR_NAME_RE}(\.{VAR_NAME_RE})*:{VAR_NAME_RE}$")
# The agent template main.py file
AGENT_TEMPLATE_URL = (
    "https://raw.githubusercontent.com/fixie-ai/fixie-examples/main/agents/template.py"
)

REQUIREMENTS_TXT = "requirements.txt"
CURRENT_FIXIE_REQUIREMENT = f"fixieai ~= {fixieai.__version__}"
FIXIE_REQUIREMENT_PATTERN = re.compile(r"^\s*fixieai([^\w]|$)")

# Environment variables for agents
FIXIE_ALLOWED_AGENT_ID = "FIXIE_ALLOWED_AGENT_ID"
FIXIE_REFRESH_ON_STARTUP = "FIXIE_REFRESH_ON_STARTUP"


@click.group(help="Agent-related commands.")
def agent():
    pass


def _slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = s.strip("-")
    return s


def _cli_revision_metadata(command: str) -> dict:
    """Returns common agent revision metadata for CLI-created revisions."""
    return {
        "fixie.ai/client": "python-cli",
        "fixie.ai/python-cli/command": command,
        "fixie.ai/python-cli/version": fixieai.__version__,
    }


def _update_agent_requirements(
    existing_requirements: List[str], new_requirements: List[str]
) -> List[str]:
    """Returns an updated list of agent requirements to go in requirements.txt."""

    # If the user specified a fixieai requirement, use that.
    fixie_requirement = next(
        filter(
            functools.partial(re.match, FIXIE_REQUIREMENT_PATTERN), new_requirements
        ),
        CURRENT_FIXIE_REQUIREMENT,
    )

    # Ensure that a compatible version of the Fixie SDK is present.
    resolved_requirements: List[str] = []

    for existing_requirement in existing_requirements:
        if (
            re.match(FIXIE_REQUIREMENT_PATTERN, existing_requirement)
            and existing_requirement != fixie_requirement
        ):
            # Ignore any existing (but different) fixieai requirements.
            continue

        resolved_requirements.append(existing_requirement)

    for new_requirement in [fixie_requirement] + new_requirements:
        if new_requirement not in resolved_requirements:
            resolved_requirements.append(new_requirement)

    return resolved_requirements


@agent.command("init", help="Creates an agent.yaml file.")
@click.option("--handle")
@click.option("--description")
@click.option("--entry-point")
@click.option("--more-info-url")
@click.option(
    "--requirement",
    multiple=True,
    type=str,
    help="Additional requirements for requirements.txt. Can be specified multiple times.",
)
@click.argument("path", required=False)
def init_agent(path, handle, description, entry_point, more_info_url, requirement):
    # Create the directory if necessary.
    path = pathlib.Path(path or ".")
    path.mkdir(parents=True, exist_ok=True)

    try:
        current_config = agent_config.load_config(path)
    except FileNotFoundError:
        current_config = agent_config.AgentConfig(handle=_slugify(path.resolve().name))

    while handle is None or not validators.slug(handle):
        if handle is not None:
            click.secho("Handle can be alpha numerics, underscores and dashes only.")
        handle = click.prompt("Handle", default=current_config.handle)

    if description is None:
        description = click.prompt("Description", default=current_config.description)

    while entry_point is None or not ENTRY_POINT_PATTERN.match(entry_point):
        if entry_point is not None:
            click.echo(
                "Entrypoint must be in module:attribute format (e.g. 'main:agent', 'main:run')"
            )

        entry_point = click.prompt(
            "Python Entrypoint (module:attribute)", default=current_config.entry_point
        )

    while more_info_url is None or not validators.url(more_info_url):
        if more_info_url is not None:
            click.echo("More info URL must be a valid URL.")

        more_info_url = click.prompt(
            "More info URL", default=current_config.more_info_url
        )
        if not more_info_url:
            break

    current_config.handle = handle
    current_config.description = description
    current_config.entry_point = entry_point
    current_config.more_info_url = more_info_url
    agent_config.save_config(current_config, path)

    entry_module, _ = entry_point.split(":")
    expected_main_path = path / (entry_module.replace(".", "/") + ".py")
    if not os.path.exists(expected_main_path):
        urllib.request.urlretrieve(AGENT_TEMPLATE_URL, expected_main_path)
        click.secho(
            f"Initialized agent.yaml and made a template agent file at {expected_main_path}",
            fg="green",
        )
    else:
        click.secho(f"Initialized agent.yaml.", fg="green")

    try:
        with open(path / REQUIREMENTS_TXT, "rt") as requirements_txt:
            existing_requirements = list(
                r.strip() for r in requirements_txt.readlines()
            )
    except FileNotFoundError:
        existing_requirements = []

    resolved_requirements = _update_agent_requirements(
        existing_requirements, list(requirement)
    )
    if not existing_requirements:
        write_requirements = True
    else:
        new_requirements = [
            r for r in resolved_requirements if r not in existing_requirements
        ]
        removed_requirements = [
            r for r in existing_requirements if r not in resolved_requirements
        ]

        if new_requirements or removed_requirements:
            click.secho(
                f"{path / REQUIREMENTS_TXT} already exists.",
                fg="yellow",
            )
            if new_requirements:
                click.secho(
                    f"The following requirements will be added: {new_requirements}",
                    fg="yellow",
                )
            if removed_requirements:
                click.secho(
                    f"The following requirements will be removed: {removed_requirements}",
                    fg="yellow",
                )
            write_requirements = click.confirm("Okay to proceed?", default=True)
        else:
            write_requirements = False

    if write_requirements:
        with open(path / REQUIREMENTS_TXT, "wt") as requirements_txt:
            requirements_txt.writelines(r + "\n" for r in resolved_requirements)


@agent.command("list", help="List agents.")
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def list_agents(ctx, verbose):
    client = ctx.obj.client
    agents = client.get_agents()
    agent_ids = sorted(agents.keys())
    for agent_id in agent_ids:
        agent = agents[agent_id]
        click.secho(f"{agent_id}", fg="green", nl=False)
        click.echo(f": {agent['name']}")
        if verbose:
            click.echo(f"    {agent['description']}")
            if "moreInfoUrl" in agent and agent["moreInfoUrl"]:
                click.secho(f"    More info", fg="yellow", nl=False)
                click.echo(f": {agent['moreInfoUrl']}")
            click.echo()


@agent.command("show", help="Show an agent.")
@click.argument("agent_id")
@click.pass_context
def show_agent(ctx, agent_id: str):
    client = ctx.obj.client
    agent = client.get_agent(agent_id)
    if not agent.valid:
        click.echo(f"Agent {agent_id} not found.")
        return
    click.secho(f"{agent.agent_id}", fg="green", nl=False)
    click.echo(f"Owner: {agent.owner}")
    if agent.name:
        click.echo(f": {agent.name}")
    if agent.description:
        click.echo(f"Description: {agent.description}")
    if agent.more_info_url:
        click.echo(f"More info URL: {agent.more_info_url}")
    click.echo(f"Published: {agent.published}")
    click.echo(f"Created: {agent.created}")
    click.echo(f"Modified: {agent.modified}")
    if agent.queries:
        click.echo(f"Queries: {agent.queries}")
    current_revision = client.get_current_agent_revision(agent_id)
    click.echo(f"Current revision: {current_revision}")


@agent.command("delete", help="Delete an agent.")
@click.argument("handle")
@click.pass_context
def delete_agent(ctx, handle: str):
    client = ctx.obj.client
    agent = client.get_agent(handle)
    agent.delete_agent()
    click.echo(f"Deleted agent {agent.agent_id}")


def _validate_agent_path(ctx, param, value):
    normalized = agent_config.normalize_path(value)
    if not os.path.exists(normalized):
        if not click.confirm(
            f"{normalized} does not exist. Would you like to create a new agent?",
            default=True,
        ):
            raise click.BadParameter(f"{normalized} does not exist")

        ctx.invoke(init_agent, path=value)

        # Re-normalize it after running init.
        normalized = agent_config.normalize_path(value)

    return normalized


def _ensure_agent_updated(
    client: fixieai.client.FixieClient,
    agent_id: str,
    config: agent_config.AgentConfig,
):
    agent = client.get_agent(agent_id)
    if not agent.valid:
        agent.create_agent(
            name=config.name,
            description=config.description,
            more_info_url=config.more_info_url,
            published=config.public or False,
        )
    else:
        agent.update_agent(
            new_handle=config.handle,
            name=config.name,
            description=config.description,
            more_info_url=config.more_info_url,
            published=config.public or False,
        )

    return agent


def _configure_venv(
    console: rich_console.Console, agent_dir: str
) -> Tuple[str, Dict[str, str]]:
    """Configures a virtual environment for the agent with its Python dependencies installed."""

    venv_path = os.path.join(agent_dir, ".fixie.venv")
    console.print(f"Configuring virtual environment in {venv_path}")

    is_windows = os.name == "nt"
    bin_path = os.path.join(venv_path, "bin" if not is_windows else "Scripts")
    python_exe = os.path.join(bin_path, "python")
    if not os.path.exists(python_exe):
        # Match `python -m venv` behavior with symlinks on non-Windows to work around https://bugs.python.org/issue38705
        venv.create(venv_path, with_pip=True, symlinks=not is_windows)
    requirements_txt_path = os.path.join(agent_dir, REQUIREMENTS_TXT)
    if not os.path.exists(requirements_txt_path):
        raise ValueError(
            f"There is no {REQUIREMENTS_TXT} file at {requirements_txt_path}, please re-run [bold]fixie init[/bold]."
        )
    subprocess.run(
        [
            python_exe,
            "-m",
            "pip",
            "install",
            "-r",
            requirements_txt_path,
            "--disable-pip-version-check",
        ]
    ).check_returncode()
    console.print(f"[green]Requirements installed successfully.[/green]")

    env = os.environ.copy()

    # Quasi-activate the venv by putting the bin directory at the front of the path
    env["PATH"] = bin_path + ":" + env.get("PATH", "")

    return python_exe, env


def _validate_agent_loads_or_exit(
    console: rich_console.Console,
    agent_dir: str,
    agent_handle: str,
    python_exe: str,
    agent_env: Dict[str, str],
):
    """Validates that an agent can successfully load and exits the current process if it can't."""
    loader_process = subprocess.run(
        [os.path.abspath(python_exe), "-m", "fixieai.cli.agent.loader"],
        env=agent_env,
        cwd=agent_dir or None,
    )
    if loader_process.returncode:
        console.print(
            f'[red]Agent "{agent_handle}" could not be loaded. If your agent requires additional dependencies '
            f"make sure they are specified in {os.path.join(agent_dir, REQUIREMENTS_TXT)}.[/red]"
        )
        sys.exit(loader_process.returncode)


@contextlib.contextmanager
def _temporary_revision_replacer(
    console: rich.console.Console, client: fixieai.FixieClient, agent_handle: str
):
    """Yields a function that can be used to temporarily replace an agent's current revision."""

    # Get the preexisting revision so that we can restore it when we're done.
    existing_revision_id = client.get_current_agent_revision(
        client.get_current_username() + "/" + agent_handle
    )
    current_temporary_revision: Optional[str] = None

    if existing_revision_id is not None:
        console.print(
            f"[yellow]This temporarily replaces existing revision {existing_revision_id}.[/yellow]"
        )

    def replace_revision(external_url: str):
        nonlocal current_temporary_revision

        # Create a new temporary revision.
        revision_to_delete = current_temporary_revision
        current_temporary_revision = client.create_agent_revision(
            handle=agent_handle,
            make_current=True,
            metadata=_cli_revision_metadata("serve"),
            external_url=external_url,
        )

        # Delete the previous temporary revision.
        if revision_to_delete:
            client.delete_agent_revision(agent_handle, revision_to_delete)

        console.print(
            f"[green]Now serving temporary revision {current_temporary_revision}.[/green]"
        )

    try:
        yield replace_revision
    finally:
        if existing_revision_id:
            client.set_current_agent_revision(agent_handle, existing_revision_id)
            console.print(
                f"[yellow]Restored existing revision {existing_revision_id}.[/yellow]"
            )

        if current_temporary_revision:
            client.delete_agent_revision(agent_handle, current_temporary_revision)


@contextlib.contextmanager
def _server_process(
    console: rich_console.Console,
    on_exit_event: threading.Event,
    python_exe: str,
    host: str,
    port: int,
    agent_env: Dict[str, str],
    agent_dir: str,
    startup_timeout_seconds: float,
):
    """Yields a Popen object with a running and ready server process."""

    with subprocess.Popen(
        [
            os.path.abspath(python_exe),
            "-m",
            "uvicorn",
            "fixieai.cli.agent.loader:uvicorn_app_factory",
            "--host",
            host,
            "--port",
            str(port),
            "--factory",
        ],
        env=agent_env,
        cwd=agent_dir or None,
    ) as popen:

        def _wait_for_exit():
            popen.wait()
            on_exit_event.set()

        waiter_thread = threading.Thread(target=_wait_for_exit, daemon=True)
        waiter_thread.start()

        try:
            # Wait for the server to start up by polling the port.
            deadline = time.monotonic() + startup_timeout_seconds
            while time.monotonic() < deadline and popen.poll() is None:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.connect(("127.0.0.1" if host == "0.0.0.0" else host, port))
                        break
                    except ConnectionRefusedError:
                        time.sleep(0.1)

            if time.monotonic() >= deadline or popen.poll() is not None:
                console.print("Server process failed to start.", style="red")
                raise click.Abort()

            yield popen
        finally:
            popen.terminate()
            waiter_thread.join()


def _wait_for_agent_changes_or_event(
    agent_dir: str, event: threading.Event
) -> Optional[str]:
    """Waits for any changes in the specified directory or the event to be set."""

    for changes in watchfiles.watch(
        agent_dir,
        watch_filter=lambda change, path: path.endswith(".py"),
        stop_event=event,
    ):
        for change, path in changes:
            return path

    return None


@agent.command(
    "serve", help="Serve the current agent locally via a publicly-accessible URL."
)
@click.argument("path", callback=_validate_agent_path, required=False)
@click.option("--host", default="0.0.0.0")
@click.option("--port", type=int, default=8181)
@click.option(
    "--tunnel/--no-tunnel",
    "use_tunnel",
    is_flag=True,
    default=True,
    help="(default enabled) Create a tunnel using localhost.run.",
)
@click.option(
    "--reload/--no-reload",
    is_flag=True,
    default=True,
    help="(default enabled) Reload automatically.",
)
@click.option(
    "--venv/--no-venv",
    "use_venv",
    is_flag=True,
    default=False,
    help="Run from virtual environment",
)
@click.pass_context
def serve(ctx, path, host, port, use_tunnel, reload, use_venv):
    console = rich_console.Console(soft_wrap=True)
    config = agent_config.load_config(path)
    client: fixieai.FixieClient = ctx.obj.client
    agent_id = f"{client.get_current_username()}/{config.handle}"

    with contextlib.ExitStack() as stack:
        agent_dir = os.path.dirname(path) or "."

        # Configure the virtual enviroment
        if use_venv:
            python_exe, agent_env = _configure_venv(console, agent_dir)
        else:
            python_exe, agent_env = sys.executable, os.environ.copy()
        agent_env[FIXIE_ALLOWED_AGENT_ID] = agent_id

        if use_tunnel:
            # Start up a tunnel via localhost.run.
            console.print(f"Opening tunnel to {host}:{port} via localhost.run.")
            deployment_urls_iter = iter(stack.enter_context(tunnel.Tunnel(port)))
        elif config.deployment_url:
            deployment_urls_iter = iter([config.deployment_url])
        else:
            console.print(
                f"[red]You must specify a deployment_url in agent.yaml or use --tunnel.[/red]"
            )
            raise click.Abort()

        agent_api = _ensure_agent_updated(client, agent_id, config)
        console.print(
            f"You can access your agent via [cyan]{client.get_agent_page_url(agent_api.agent_id)}[/]"
            f" or `[green]fixie console --agent {agent_api.agent_id}[/]`."
        )

        replace_revision = stack.enter_context(
            _temporary_revision_replacer(console, client, config.handle)
        )

        # An Event that indicates that either the subprocess exited or the tunnel URL has been rotated.
        requires_action = threading.Event()
        current_url = next(deployment_urls_iter)

        def _watch_tunnel():
            """Watches the tunnel for URL rotations."""
            nonlocal current_url

            while True:
                try:
                    current_url = next(deployment_urls_iter)
                except StopIteration:
                    return
                finally:
                    requires_action.set()

        threading.Thread(target=_watch_tunnel, daemon=True).start()

        while True:
            requires_action.clear()

            with _server_process(
                console,
                requires_action,
                python_exe,
                host,
                port,
                agent_env,
                agent_dir,
                startup_timeout_seconds=10.0,
            ) as popen:
                # The server has started up, so we can replace the revision.
                replace_revision(current_url)

                while True:
                    if reload:
                        changed_file = _wait_for_agent_changes_or_event(
                            agent_dir, requires_action
                        )
                        if changed_file is not None:
                            console.print(
                                f"[yellow]{changed_file} was changed. Restarting server.[/yellow]"
                            )
                            break
                        else:
                            assert requires_action.is_set()

                    requires_action.wait()
                    requires_action.clear()

                    if popen.poll() is not None:
                        console.print(
                            "The server process stopped, exiting.",
                            style="red" if popen.returncode != 0 else None,
                        )
                        raise click.exceptions.Exit(popen.returncode)
                    else:
                        # The tunnel URL changed.
                        replace_revision(current_url)


_DEPLOYMENT_BOOTSTRAP_SOURCE = """
import os

import dotenv

if __name__ == "__main__":
    dotenv.load_dotenv()
    os.chdir("agent")

    # N.B. Load the .dotenv file before loading the Fixie SDK
    import uvicorn

    from fixieai.cli.agent import loader
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(loader.uvicorn_app_factory(), host="0.0.0.0", port=port)
"""


@contextmanager
def _spinner(console: rich_console.Console, text: str):
    """A context manager that renders a spinner and ✅/❌ on completion."""

    try:
        with console.status(text):
            yield
        console.print(f":white_check_mark: {text}")
    except:
        console.print(f":cross_mark: {text}")
        raise


def _tarinfo_filter(
    console: rich_console.Console, root: str, tar_prefix: str, tarinfo: tarfile.TarInfo
) -> Optional[tarfile.TarInfo]:
    """Filters out hidden files from being included in a tarball."""

    basename = os.path.basename(tarinfo.name)
    if basename.startswith(".") and basename != ".env":
        original_path = tarinfo.name
        if original_path.startswith(tar_prefix):
            original_path = original_path[len(tar_prefix) :]

        original_path = os.path.join(root, original_path)
        console.print(
            f"Ignoring hidden {'directory' if tarinfo.isdir() else 'file'} {original_path}",
            style="grey53",
        )
        return None
    else:
        return tarinfo


def _add_text_file_to_tarfile(path: str, text: str, tarball: tarfile.TarFile):
    file_bytes = text.encode("utf-8")
    tarinfo = tarfile.TarInfo(path)
    tarinfo.size = len(file_bytes)
    tarball.addfile(tarinfo, io.BytesIO(file_bytes))


@contextlib.contextmanager
def _agent_py_code_package(
    agent_dir: str, agent_id: str, console: rich_console.Console
):
    """Yields a file-like code package that can be deployed to Fixie."""

    with tempfile.TemporaryFile() as tarball_file:
        with tarfile.open(fileobj=tarball_file, mode="w:gz") as tarball:
            tarball.add(
                agent_dir,
                arcname="agent",
                filter=functools.partial(_tarinfo_filter, console, agent_dir, "agent/"),
            )

            # Add the bootstrapping code and environment variables
            _add_text_file_to_tarfile("main.py", _DEPLOYMENT_BOOTSTRAP_SOURCE, tarball)
            _add_text_file_to_tarfile(
                ".env",
                "\n".join(
                    f"{key}={value}"
                    for key, value in {
                        FIXIE_ALLOWED_AGENT_ID: agent_id,
                        "FIXIE_API_URL": constants.FIXIE_API_URL,
                    }.items()
                ),
                tarball,
            )

        tarball_file.seek(0)
        yield tarball_file


@contextlib.contextmanager
def _agent_js_code_package(
    agent_dir: str, agent_id: str, console: rich_console.Console
):
    package_json_path = os.path.join(agent_dir, "package.json")
    with open(package_json_path) as package_json_file:
        package_json = json.load(package_json_file)
    tgz_name = package_json["name"] + "-" + package_json["version"] + ".tgz"
    subprocess.check_call(["npm", "pack"], cwd=agent_dir)
    tarball_file = open(tgz_name, "rb")
    yield tarball_file


@agent.command("deploy", help="Deploy the current agent.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.option(
    "--metadata-only",
    is_flag=True,
    default=None,
    help="(No longer supported.)",
)
@click.option("--public", is_flag=True, help="Make the agent public.", default=None)
@click.option(
    "--validate/--no-validate",
    "validate",
    is_flag=True,
    default=True,
    help="(default enabled) Validate that the agent loads in a local venv before deploying.",
)
@click.option(
    "--current/--not-current",
    "make_current",
    is_flag=True,
    default=True,
    help="(default enabled) Change the current revision to the deployed revision.",
)
@click.option(
    "--metadata",
    nargs=2,
    type=str,
    help="Additional metadata to associate with the revision.",
    multiple=True,
)
@click.option(
    "--reindex/--no-reindex",
    "reindex",
    is_flag=True,
    default=False,
    help="Force any corpora to be reindexed.",
)
@click.pass_context
def deploy(ctx, path, metadata_only, public, validate, make_current, metadata, reindex):
    console = rich_console.Console(soft_wrap=True)
    if metadata_only is not None:
        console.print(
            "[yellow]Warning:[/] The [blue]--metadata-only[/] option is no longer supported."
        )

    config = agent_config.load_config(path)
    if config.public is not None:
        console.print(
            "[yellow]Warning:[/] The [blue]`public`[/] option in the agent config is deprecated and will be removed soon."
        )
        console.print(
            "[yellow]Warning:[/] Use [blue]`fixie agent deploy --public`[/] instead."
        )
    if public:
        config.public = True

    client: fixieai.FixieClient = ctx.obj.client
    agent_id = f"{client.get_current_username()}/{config.handle}"
    console.print(f"🦊 Deploying agent [green]{agent_id}[/]...")

    agent_dir = os.path.dirname(path) or "."
    package_json_path = os.path.join(agent_dir, "package.json")
    is_js_agent = os.path.exists(package_json_path)
    if validate and not is_js_agent:
        # Validate that the agent loads in a virtual environment before deploying.
        python_exe, agent_env = _configure_venv(console, agent_dir)
        agent_env[FIXIE_ALLOWED_AGENT_ID] = agent_id
        _validate_agent_loads_or_exit(
            console, agent_dir, config.handle, python_exe, agent_env
        )

    _ = _ensure_agent_updated(client, agent_id, config)

    metadata_dict = {**dict(metadata or []), **_cli_revision_metadata("deploy")}

    if config.deployment_url is None:
        # Deploy the code to Fixie.
        if is_js_agent:
            with _agent_js_code_package(
                agent_dir, agent_id, console
            ) as tarball_file, _spinner(console, "Deploying JS..."):
                revision_id = client.create_agent_revision(
                    config.handle,
                    make_current=make_current,
                    metadata=metadata_dict,
                    javascript_gzip_tarfile=tarball_file,
                    reindex_corpora=reindex,
                )
        else:
            with _agent_py_code_package(
                agent_dir, agent_id, console
            ) as tarball_file, _spinner(console, "Deploying Python..."):
                revision_id = client.create_agent_revision(
                    config.handle,
                    make_current=make_current,
                    metadata=metadata_dict,
                    python_gzip_tarfile=tarball_file,
                    reindex_corpora=reindex,
                )
    else:
        # Create a new revision with the specified URL.
        with _spinner(console, "Deploying..."):
            revision_id = client.create_agent_revision(
                config.handle,
                make_current=make_current,
                metadata=metadata_dict,
                external_url=config.deployment_url,
                reindex_corpora=reindex,
            )

    sample_queries = client.gqlclient.execute(
        gql(
            """
            query GetSampleQueries($agentId: String!) {
                agentById(agentId: $agentId) {
                    queries
                }
            }
            """
        ),
        variable_values={"agentId": agent_id},
    )

    if sample_queries["agentById"]["queries"]:
        suggested_query = random.choice(sample_queries["agentById"]["queries"])
    else:
        suggested_query = "Hello!"

    console.print(
        f"Revision {revision_id} was deployed to {constants.FIXIE_API_URL}/agents/{agent_id}\n"
        f"You can also chat with your agent using the fixie CLI:\n\n"
        f"fixie console --agent {agent_id} {shlex.quote(suggested_query)}"
    )


@agent.command("publish", help="Make the current agent public.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.pass_context
def publish(ctx, path):
    console = rich_console.Console(soft_wrap=True)
    config = agent_config.load_config(path)
    if config.public is not None:
        console.print(
            "[yellow]Warning:[/] The [blue]`public`[/] option in the agent config is deprecated and will be removed soon."
        )
    client: fixieai.FixieClient = ctx.obj.client
    agent_id = f"{client.get_current_username()}/{config.handle}"
    console.print(f"🦊 Publishing agent [green]{agent_id}[/]...")

    agent = client.get_agent(agent_id)
    if not agent.valid:
        console.print(
            f"[red]Error:[/] Agent [green]{agent_id}[/] not deployed. Use [blue]`fixie agent deploy`[/] to deploy it."
        )
        raise click.Abort()
    agent.update_agent(published=True)

    console.print(f"Agent [green]{agent_id}[/] has been made public.")


@agent.command("unpublish", help="Make the current agent not public.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.pass_context
def unpublish(ctx, path):
    console = rich_console.Console(soft_wrap=True)
    config = agent_config.load_config(path)
    if config.public is not None:
        console.print(
            "[yellow]Warning:[/] The [blue]`public`[/] option in the agent config is deprecated and will be removed soon."
        )
    client: fixieai.FixieClient = ctx.obj.client
    agent_id = f"{client.get_current_username()}/{config.handle}"
    console.print(f"🦊 Unpublishing agent [green]{agent_id}[/]...")

    agent = client.get_agent(agent_id)
    if not agent.valid:
        console.print(
            f"[red]Error:[/] Agent [green]{agent_id}[/] not deployed. Use [blue]`fixie agent deploy`[/] to deploy it."
        )
        raise click.Abort()
    agent.update_agent(published=False)

    console.print(f"Agent [green]{agent_id}[/] has been made private.")


@agent.group(help="Revisions-related commands.")
def revisions():
    pass


@revisions.command("list", help="Lists the revisions associated with an agent.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.option("--json", is_flag=True, default=False)
@click.pass_context
def list_revisions(ctx, path, json):
    console = rich_console.Console(soft_wrap=True)
    config = agent_config.load_config(path)

    client: fixieai.FixieClient = ctx.obj.client
    agent_id = f"{client.get_current_username()}/{config.handle}"
    agent = client.get_agent(agent_id)
    if not agent.valid:
        console.print(
            f"[red]Error:[/] Agent [green]{agent_id}[/] not deployed. Use [blue]`fixie agent deploy`[/] to deploy it."
        )
        raise click.Abort()

    query = gql(
        """
        query GetRevisions($agentId: String!) {
            agentById(agentId: $agentId) {
                allRevisions {
                    id
                    created
                    isCurrent
                    indexedCorpora {
                        status
                        created
                        modified
                        vectorCount
                    }
                    deployment {
                        __typename
                        ... on ExternalDeployment {
                            url
                        }
                        ... on ManagedDeployment {
                            environment
                        }
                    }
                    metadata {
                        key
                        value
                    }
                }
            }
        }
        """
    )
    revisions = client.gqlclient.execute(query, variable_values={"agentId": agent_id})[
        "agentById"
    ]["allRevisions"]

    if json:
        console.print_json(data=revisions)
    else:
        table = rich.table.Table(title=f"{agent_id} revisions")
        table.add_column("ID", no_wrap=True)
        table.add_column("Date")
        table.add_column("Deployment")

        has_corpora = False
        if any(revision["indexedCorpora"] for revision in revisions):
            table.add_column("Indexed")
            has_corpora = True

        table.add_column("Current")

        for revision in revisions:
            row = [
                revision["id"],
                revision["created"],
            ]

            deployment = revision["deployment"]
            if deployment is None:
                row.append("-")
            elif deployment["__typename"] == "ExternalDeployment":
                row.append(deployment["url"])
            elif deployment["__typename"] == "ManagedDeployment":
                row.append(f"Fixie-hosted {deployment['environment'].title()}")
            else:
                row.append("?")

            if has_corpora:
                indexes = revision["indexedCorpora"] or []
                if any(index["status"] == "FAILED" for index in indexes):
                    row.append("❌")
                elif any(index["status"] == "IN_PROGRESS" for index in indexes):
                    row.append("⏳")
                elif indexes and all(
                    index["status"] == "COMPLETED" for index in indexes
                ):
                    row.append("✅")
                else:
                    row.append("")

            row.append("✅" if revision["isCurrent"] else "")

            table.add_row(*row)

        console.print(table)


@revisions.command(
    "set-current", help="Sets the current (active) revision of an agent."
)
@click.argument("path", callback=_validate_agent_path, required=False)
@click.option("--id", required=True, help="The revision ID to make current.")
@click.pass_context
def set_current_revision(ctx, path, id):
    console = rich_console.Console(soft_wrap=True)
    config = agent_config.load_config(path)

    client: fixieai.FixieClient = ctx.obj.client
    client.set_current_agent_revision(config.handle, id)
    console.print(f"Set current revision to {id}.")


@revisions.command("delete", help="Deletes a revision of an agent.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.option("--id", required=True, help="The revision ID to delete.")
@click.option("--force/-f", help="Delete the revision even if it is the current one.")
@click.pass_context
def delete_revision(ctx, path, id, force):
    console = rich_console.Console(soft_wrap=True)
    config = agent_config.load_config(path)

    client: fixieai.FixieClient = ctx.obj.client

    current_revision = client.get_current_agent_revision(
        client.get_current_username() + "/" + config.handle
    )
    if current_revision == id:
        if not force:
            console.print(
                f"Not deleting revision {id} because it is the current revision. (Use --force to delete it anyway.)",
                style="red",
            )
            raise click.exceptions.Exit(1)
        else:
            console.print(
                f"Deleting current revision {id} because --force was set. This will prevent the agent from responding to requests.",
                style="yellow",
            )

    client.delete_agent_revision(config.handle, id)
    console.print(f"Deleted revision {id}.")
