import os

import click
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
            deployment_url=config.deployment_url,
            published=config.public,
        )
    else:
        agent.update_agent(
            new_handle=config.handle,
            name=config.name,
            description=config.description,
            more_info_url=config.more_info_url,
            deployment_url=config.deployment_url,
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


@agent.command("deploy", help="Deploy the current agent.")
@click.argument("path", callback=_validate_agent_path, required=False)
@click.pass_context
def deploy(ctx, path):
    config = agent_config.load_config(path)
    agent_api = _ensure_agent_updated(ctx.obj.client, config)
    if config.deployment_url is None:
        raise NotImplementedError("Managed deployment is not yet implemented")

    # Trigger a refresh with the updated deployment
    ctx.obj.client.refresh_agent(config.handle)
