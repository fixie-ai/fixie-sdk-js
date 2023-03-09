import io
import os
from contextlib import contextmanager
from typing import BinaryIO, Dict

import click
import rich.console as rich_console
import validators

import fixieai.client
from fixieai.cli.agent import agent_config
from fixieai.cli.agent import loader


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
            click.secho(f"{param.name} must be a valid url.")
            value = click.prompt(param.prompt, default=param.default())
        else:
            return value


@agent.command("init", help="Creates an agent.yaml file.")
@click.option(
    "--handle",
    prompt=True,
    default=lambda: _current_config().handle,
    callback=_validate_slug,
)
@click.option(
    "--description",
    prompt=True,
    default=lambda: _current_config().description,
)
@click.option(
    "--entry-point",
    prompt=True,
    default=lambda: _current_config().entry_point,
)
@click.option(
    "--more-info-url",
    prompt=True,
    default=lambda: _current_config().more_info_url,
    callback=_validate_url,
)
@click.option(
    "--public",
    prompt=True,
    default=lambda: _current_config().public,
    type=click.BOOL,
)
def init_agent(handle, description, entry_point, more_info_url, public):
    try:
        current_config = agent_config.load_config()
    except FileNotFoundError:
        current_config = agent_config.AgentConfig()
    current_config.handle = handle
    current_config.description = description
    current_config.entry_point = entry_point
    current_config.more_info_url = more_info_url
    current_config.public = public
    agent_config.save_config(current_config)


def _current_config() -> agent_config.AgentConfig:
    """Loads current agent config, or a default if not initialized."""
    try:
        return agent_config.load_config()
    except FileNotFoundError:
        return agent_config.AgentConfig()


@agent.command("list", help="List agents.")
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def list_agents(ctx, verbose):
    client = ctx.obj.client
    agents = client.get_agents()
    for agent_id, agent in agents.items():
        click.secho(f"{agent_id}", fg="green", nl=False)
        click.echo(f": {agent['name']}")
        if verbose:
            click.echo(f"    {agent['description']}")
            if "moreInfoUrl" in agent and agent["moreInfoUrl"]:
                click.secho(f"    More info", fg="yellow", nl=False)
                click.echo(f": {agent['moreInfoUrl']}")
            click.echo()


def _validate_agent_path(ctx, param, value):
    normalized = agent_config.normalize_path(value)
    if not os.path.exists(normalized):
        raise click.BadParameter(f"{normalized} does not exist")
    return normalized


def _ensure_agent_updated(
    client: fixieai.client.FixieClient,
    config: agent_config.AgentConfig,
):
    agent = client.get_agent(config.handle)
    if agent.agent_id is None:
        agent.create_agent(
            name=config.name,
            description=config.description,
            more_info_url=config.more_info_url,
            func_url=config.deployment_url,
            published=config.public,
        )
    else:
        agent.update_agent(
            new_handle=config.handle,
            name=config.name,
            description=config.description,
            more_info_url=config.more_info_url,
            func_url=config.deployment_url,
            published=config.public,
        )

    return agent


@agent.command("serve", help="Start serving the current agent.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.option("--host", default="0.0.0.0")
@click.option("--port", type=int, default=8181)
@click.pass_context
def serve(ctx, path, host, port):
    # TODO: add tunneling and deployment url update
    config, agent_impl = loader.load_agent_from_path(path)
    agent_api = _ensure_agent_updated(ctx.obj.client, config)
    agent_impl.serve(agent_api.agent_id, host, port)


_DEPLOYMENT_BOOTSTRAP_SOURCE = """
import os
from fixieai.cli.agent import loader

if __name__ == "__main__":    
    config, agent = loader.load_agent_from_path("agent")
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


@agent.command("deploy", help="Deploy the current agent.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.pass_context
def deploy(ctx, path):
    console = rich_console.Console()
    config = agent_config.load_config(path)
    agent_api = _ensure_agent_updated(ctx.obj.client, config)

    if config.deployment_url is None:
        # Deploy the agent to fixie with some bootstrapping code.
        file_streams: Dict[str, BinaryIO] = {}
        deploy_root = os.path.dirname(path)
        for root, dirs, files in os.walk(deploy_root, topdown=True):
            # Exclude any hidden files by removing them from the dirs list.
            # As per https://docs.python.org/3/library/os.html#os.walk
            # removing them from the dirs list with topdown=True skips
            # them from the walk.
            for i, dir in reversed(list(enumerate(dirs))):
                if dir.startswith("."):
                    console.print(
                        f"Ignoring hidden directory {os.path.join(root, dir)}",
                        style="grey53",
                    )
                    # N.B. We're iterating in reverse to avoid needing to adjust i.
                    del dirs[i]

            for filename in files:
                if filename.startswith("."):
                    console.print(
                        f"Ignoring hidden file {os.path.join(root, filename)}",
                        style="grey53",
                    )
                    continue

                full_path = os.path.join(root, filename)
                upload_path = os.path.join(
                    "agent", os.path.relpath(full_path, deploy_root)
                )
                file_streams[upload_path] = open(full_path, "rb")

        file_streams["main.py"] = io.BytesIO(_DEPLOYMENT_BOOTSTRAP_SOURCE.encode())
        with _spinner(console, "Deploying..."):
            ctx.obj.client.deploy_agent(
                config.handle,
                file_streams,
            )

    # Trigger a refresh with the updated deployment
    with _spinner(console, "Refreshing..."):
        ctx.obj.client.refresh_agent(config.handle)
