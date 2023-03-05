#!/usr/bin/env python3

import click
import rich.console as rich_console

import fixieai
from fixieai import constants
from fixieai.cli import auth
from fixieai.cli import agent_config
from fixieai.cli import console

textconsole = rich_console.Console()


#######  fixie CLI definition  #######


@click.group()
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def fixie(ctx, verbose):
    """fixie CLI to run and deploy agents."""
    ctx.ensure_object(dict)
    client = fixieai.FixieClient()
    ctx.obj["CLIENT"] = client
    ctx.obj["VERBOSE"] = verbose


############  fixie auth  ############


@fixie.command("auth", help="Authenticate to fixie and save credentials.")
@click.option("--force", "-f", is_flag=True)
def authenticate(force: bool):
    if not force:
        try:
            constants.fixie_api_key()
            click.echo("User is already authenticated. Set --force to override.")
            return
        except ValueError:
            pass
    auth.authentication_flow()


############  fixie init  ############


@fixie.command("init", help="Creates an agent.yaml file.")
def init():
    try:
        current_config = agent_config.load_config()
    except FileNotFoundError:
        current_config = agent_config.AgentConfig()
    agent_config.prompt_user(current_config)
    agent_config.save_config(current_config)


############  fixie agent  ############


@fixie.group(help="Agent-related commands.")
def agent():
    pass


@agent.command("list", help="List agents.")
@click.pass_context
def list_agents(ctx):
    client = ctx.obj["CLIENT"]
    agents = client.get_agents()
    for agent_id, agent in agents.items():
        textconsole.print(f"[green]{agent_id}[/]: {agent['name']}")
        if ctx.obj["VERBOSE"]:
            textconsole.print(f"    {agent['description']}")
            textconsole.print(f"    [yellow]Developer[/]: {agent['developer']}")
            if "moreInfo" in agent and agent["moreInfo"]:
                textconsole.print(f"    [yellow]More info[/]: {agent['moreInfo']}")
            textconsole.print("")


############  fixie session  ############


@fixie.group(help="Session-related commands.")
def sessions():
    pass


@sessions.command("list", help="List sessions.")
@click.pass_context
def list_sessions(ctx):
    client = ctx.obj["CLIENT"]
    session_ids = client.get_sessions()
    for session_id in session_ids:
        textconsole.print(f"[green]{session_id}[/]")


@sessions.command("new", help="Creates a new session and opens it.")
@click.pass_context
def new_session(ctx):
    client = ctx.obj["CLIENT"]
    c = console.Console(client)
    c.run()


@sessions.command("open", help="Show session.")
@click.pass_context
@click.argument("session_id")
def open_session(ctx, session_id: str):
    client = ctx.obj["CLIENT"]
    session = client.get_session(session_id)
    messages = session.get_messages()
    textconsole.print(messages)


if __name__ == "__main__":
    fixie()
