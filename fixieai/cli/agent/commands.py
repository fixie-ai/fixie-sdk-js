import contextlib
import functools
import io
import json
import os
import random
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.request
import venv
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

import click
import rich.console as rich_console
import validators

import fixieai.client
from fixieai import constants
from fixieai.cli.agent import agent_config
from fixieai.cli.agent import tunnel

# Regex pattern to match valid entry points: "module:object"
VAR_NAME_RE = r"(?![0-9])\w+"
ENTRY_POINT_PATTERN = re.compile(rf"^{VAR_NAME_RE}(\.{VAR_NAME_RE})*:{VAR_NAME_RE}$")

REQUIREMENTS_TXT = "requirements.txt"
CURRENT_FIXIE_REQUIREMENT = f"fixieai ~= {fixieai.__version__}"
FIXIE_REQUIREMENT_PATTERN = re.compile(r"^\s*fixieai([^\w]|$)")

# Environment variables for agents
FIXIE_ALLOWED_AGENT_ID = "FIXIE_ALLOWED_AGENT_ID"
FIXIE_REFRESH_ON_STARTUP = "FIXIE_REFRESH_ON_STARTUP"


@click.group(help="Agent-related commands.")
def agent():
    pass


def _validate_slug(ctx, param, value):
    while True:
        if not validators.slug(value):
            click.secho(
                f"{param.name} can be alpha numerics, underscores and dashes only."
            )
            value = click.prompt(param.prompt, default=param.default())
        else:
            return value


def _validate_url(ctx, param, value):
    while True:
        if value and not validators.url(value):
            click.echo(f"{param.name} must be a valid url.")
            value = click.prompt(param.prompt, default=param.default())
        else:
            return value


def _validate_entry_point(ctx, param, value):
    while True:
        if value and not ENTRY_POINT_PATTERN.match(value):
            click.echo(
                f"{param.name} must be in module:obj format (e.g. 'main:agent'), but was: {value}"
            )
            value = click.prompt(param.prompt, default=param.default())
        else:
            return value


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


def config_already_exists():
    try:
        agent_config.load_config()
        return True
    except FileNotFoundError:
        return False


@agent.command("init", help="Creates an agent.yaml file.")
@click.option(
    "--handle",
    prompt=True,
    default=agent_config.AgentConfig().handle,
    callback=_validate_slug,
)
@click.option(
    "--description",
    prompt=True,
    default=agent_config.AgentConfig().description,
)
@click.option(
    "--language",
    type=click.Choice(["python", "py", "typescript", "TS"], case_sensitive=False),
    default="python",
    prompt=True,
    help="Build your agent in Python or TypeScript.",
)
# It would be nice if we could prevent `--entry-point` from being passed when language is TS, but I wasn't able to make that work after ~30 minutes.
#
# Additionally, if you first generate a TS project, then run `init --language py`,
# this will product a somewhat awkward (but I think ultimately understandable) message.
@click.option(
    "--entry-point",
    prompt=False,
    help="Entry point (module:object) (This is only used for Python agents.)",
    default="main:agent",
    callback=_validate_entry_point,
)
@click.option(
    "--more-info-url",
    prompt=True,
    default=agent_config.AgentConfig().more_info_url,
    callback=_validate_url,
)
@click.option(
    "--requirement",
    multiple=True,
    type=str,
    help="Additional requirements for requirements.txt. Can be specified multiple times.",
)
def init_agent(handle, description, entry_point, more_info_url, requirement, language):
    if config_already_exists():
        click.secho(
            f"An agent.yaml file already exists in this directory. If you want to create a new agent, please run this command in a different directory, or remove agent.yaml.",
            fg="yellow",
        )
        sys.exit(1)

    is_typescript = language.lower() in ["typescript", "ts"]

    current_config = agent_config.AgentConfig()
    current_config.handle = handle
    current_config.description = description
    current_config.entry_point = entry_point
    current_config.language = "typescript" if is_typescript else "python"
    current_config.more_info_url = more_info_url

    entry_module, _ = entry_point.split(":")
    main_file_extension = ".py"
    agent_template_url = "https://raw.githubusercontent.com/fixie-ai/fixie-examples/main/agents/template.py"

    if is_typescript:
        main_file_extension = ".ts"
        # Before merging to main, update this to match the Python version.
        agent_template_url = "https://raw.githubusercontent.com/fixie-ai/fixie-sdk/feature-ts/fixieai/agents-ts/src/template.ts"

        current_config.entry_point = "index.ts"
        expected_main_path = 'index.ts'
    else:
        expected_main_path = entry_module.replace(".", "/") + main_file_extension

    agent_config.save_config(current_config)

    if not os.path.exists(expected_main_path):
        urllib.request.urlretrieve(agent_template_url, expected_main_path)
        click.secho(
            f"Initialized agent.yaml and made a template agent file at {expected_main_path}",
            fg="green",
        )
    else:
        click.secho(f"Initialized agent.yaml.", fg="green")

    if is_typescript:

        def write_json_file_if_not_exists(filename: str, data: Dict) -> None:
            if os.path.exists(filename):
                click.secho(
                    f"Not writing {filename} because it already exists.",
                    fg="yellow",
                )
                return

            with open(filename, "wt") as f:
                json.dump(data, f, indent=2)

        package_json = {
            "name": handle,
            "version": "1.0.0",
            "description": description,
            "main": expected_main_path,
            "scripts": {"test": 'echo "Error: no test specified" && exit 1'},
            "license": "ISC",
            "devDependencies": {
                "@tsconfig/node18": "^1.0.1",
            },
            "dependencies": {"fixieai": "^1.0.0"},
        }

        tsconfig = {
            # Keeping this up to date may become annoying, but we can deal with that later.
            "extends": "@tsconfig/node18/tsconfig.json",
            "compilerOptions": {"noEmit": True},
        }

        write_json_file_if_not_exists("package.json", package_json)
        write_json_file_if_not_exists("tsconfig.json", tsconfig)
    else:
        try:
            with open(REQUIREMENTS_TXT, "rt") as requirements_txt:
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
                    f"{REQUIREMENTS_TXT} already exists.",
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
            with open(REQUIREMENTS_TXT, "wt") as requirements_txt:
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
    if agent.func_url:
        click.echo(f"Func URL: {agent.func_url}")
    if agent.query_url:
        click.echo(f"Query URL: {agent.query_url}")
    click.echo(f"Created: {agent.created}")
    click.echo(f"Modified: {agent.modified}")
    if agent.queries:
        click.echo(f"Queries: {agent.queries}")


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
        raise click.BadParameter(f"{normalized} does not exist")
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
            func_url=config.deployment_url,
            published=config.public or False,
        )
    else:
        agent.update_agent(
            new_handle=config.handle,
            name=config.name,
            description=config.description,
            more_info_url=config.more_info_url,
            func_url=config.deployment_url,
            published=config.public or False,
        )

    return agent


def _configure_venv(
    console: rich_console.Console, agent_dir: str
) -> Tuple[str, Dict[str, str]]:
    """Configures a virtual environment for the agent with its Python dependencies installed."""

    venv_path = os.path.join(agent_dir, ".fixie.venv")
    console.print(f"Configuring virtual environment in {venv_path}")
    python_exe = os.path.join(venv_path, "bin", "python")
    if not os.path.exists(python_exe):
        venv.create(venv_path, with_pip=True)
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
    env["PATH"] = os.path.join(venv_path, "bin") + ":" + env.get("PATH", "")

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
        [python_exe, "-m", "fixieai.cli.agent.loader"],
        env=agent_env,
        cwd=agent_dir or None,
    )
    if loader_process.returncode:
        console.print(
            f'[red]Agent "{agent_handle}" could not be loaded. If your agent requires additional dependencies '
            f"make sure they are specified in {os.path.join(agent_dir, REQUIREMENTS_TXT)}.[/red]"
        )
        sys.exit(loader_process.returncode)


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
    "use_venv_flag",
    is_flag=True,
    default=False,
    help="Run from virtual environment [Only used for Python agents]",
)
@click.pass_context
def serve(ctx, path, host, port, use_tunnel, reload, use_venv_flag):
    console = rich_console.Console(soft_wrap=True)
    config = agent_config.load_config(path)
    is_typescript = config.language == "typescript"
    client: fixieai.FixieClient = ctx.obj.client
    agent_id = f"{client.get_current_username()}/{config.handle}"

    if is_typescript and use_venv_flag:
        console.print(
            "[yellow]Warning: passing --venv has no effect for TypeScript agents.[/yellow]"
        )
    # Ignore the --venv flag for TypeScript agents.
    use_venv = use_venv_flag and not is_typescript

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
            console.print(
                f"[yellow]This replaces any existing deployment. Run [bold]fixie deploy[/bold] to redeploy to prod.[/yellow]"
            )
            deployment_urls_iter = iter(stack.enter_context(tunnel.Tunnel(port)))
            config.deployment_url = next(deployment_urls_iter)

            agent_api = _ensure_agent_updated(client, agent_id, config)

            def _watch_tunnel():
                while True:
                    url = next(deployment_urls_iter, None)
                    if url is None:
                        break
                    agent_api.update_agent(func_url=url)
                    console.print(
                        f"[yellow]Tunnel URL was updated. Now serving via {url}[/yellow]"
                    )

            threading.Thread(target=_watch_tunnel, daemon=True).start()
        else:
            agent_api = _ensure_agent_updated(client, agent_id, config)

        console.print(
            f"🦊 Agent [green]{agent_api.agent_id}[/] running locally on {host}:{port}, served via {agent_api.func_url}. Run `fixie console` in another terminal window to interact with this agent. In `fixie console`, send a command like \"@{agent_api.agent_id} hello world\" to talk to your agent."
        )

        # Trigger an agent refresh each time it reloads.
        agent_env[FIXIE_REFRESH_ON_STARTUP] = "true"
        if is_typescript:
            # Get path from this file to ../../agents-ts/dist/serve-bin.js
            serve_bin_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "agents-ts", "dist", "serve-bin.js"
            )
            print(client.get_refresh_agent_url(agent_id))

            subprocess.run([
                serve_bin_path,
                "--port",
                str(port),
                "--agent",
                path,
                "--silentStartup",
                "--refreshMetadataAPIUrl",
                client.get_refresh_agent_url(agent_id),
            ]).check_returncode()
        else:
            subprocess.run(
                [
                    python_exe,
                    "-m",
                    "uvicorn",
                    "fixieai.cli.agent.loader:uvicorn_app_factory",
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--factory",
                ]
                + (["--reload"] if reload else []),
                env=agent_env,
                cwd=agent_dir or None,
            ).check_returncode()

_DEPLOYMENT_BOOTSTRAP_SOURCE = """
import os

import dotenv

if __name__ == "__main__":
    dotenv.load_dotenv()
    os.chdir("agent")

    # N.B. Load the .dotenv file before loading the Fixie SDK
    from fixieai.cli.agent import loader
    config, agent = loader.load_agent_from_path(".")
    agent.serve(port=int(os.getenv("PORT", "8080")))
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


@agent.command("deploy", help="Deploy the current agent.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.option(
    "--metadata-only",
    is_flag=True,
    help="Only publish metadata and refresh, do not redeploy.",
)
@click.option("--public", is_flag=True, help="Make the agent public.", default=None)
@click.option(
    "--validate/--no-validate",
    "validate",
    is_flag=True,
    default=True,
    help="(default enabled) Validate that the agent loads in a local venv before deploying",
)
@click.pass_context
def deploy(ctx, path, metadata_only, public, validate):
    console = rich_console.Console(soft_wrap=True)
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
    if validate:
        # Validate that the agent loads in a virtual environment before deploying.
        python_exe, agent_env = _configure_venv(console, agent_dir)
        agent_env[FIXIE_ALLOWED_AGENT_ID] = agent_id
        _validate_agent_loads_or_exit(
            console, agent_dir, config.handle, python_exe, agent_env
        )

    agent_api = _ensure_agent_updated(client, agent_id, config)

    if config.deployment_url is None and not metadata_only:
        # Deploy the agent to fixie with some bootstrapping code.
        with tempfile.TemporaryFile() as tarball_file:
            with tarfile.open(fileobj=tarball_file, mode="w:gz") as tarball:
                tarball.add(
                    agent_dir,
                    arcname="agent",
                    filter=functools.partial(
                        _tarinfo_filter, console, agent_dir, "agent/"
                    ),
                )

                # Add the bootstrapping code and environment variables
                _add_text_file_to_tarfile(
                    "main.py", _DEPLOYMENT_BOOTSTRAP_SOURCE, tarball
                )
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
            with _spinner(console, "Deploying..."):
                ctx.obj.client.deploy_agent(
                    config.handle,
                    tarball_file,
                )

    # Trigger a refresh with the updated deployment
    with _spinner(console, "Refreshing..."):
        client.refresh_agent(config.handle)

    agent_api.update_agent()
    if agent_api.queries:
        suggested_query = random.choice(agent_api.queries)
    else:
        suggested_query = "Hello!"

    suggested_command = (
        f"fixie console --agent {agent_api.agent_id} {shlex.quote(suggested_query)}"
    )
    console.print(
        f"Your agent was deployed to {constants.FIXIE_API_URL}/agents/{agent_api.agent_id}\nYou can also chat with your agent using the fixie CLI:\n\n{suggested_command}"
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
