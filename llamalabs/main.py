#!/usr/bin/env python3

import click
import rich.console as rich_console

import llamalabs

textconsole = rich_console.Console()


@click.group()
@click.option(
    "--llamalabs_api_url",
    help="Llama Labs API URL. Defaults to the value of the LLAMALABS_API_URL env var, or `https://app.llamalabs.ai` if that is unset.",
)
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def cli(ctx, llamalabs_api_url, verbose):
    ctx.ensure_object(dict)
    client = llamalabs.LlamaLabsClient(api_url=llamalabs_api_url)
    ctx.obj["LLAMALABS_API_URL"] = llamalabs_api_url
    ctx.obj["CLIENT"] = client
    ctx.obj["VERBOSE"] = verbose


@cli.command("console", help="Run live console.")
@click.pass_context
def console(ctx):
    client = ctx.obj["CLIENT"]
    c = llamalabs.Console(client)
    c.run()


@cli.group(help="Agent-related commands.")
def agents():
    pass


@agents.command("list", help="List agents.")
@click.pass_context
def list_agents(ctx):
    client = ctx.obj["CLIENT"]
    agents = client.agents()
    for agent_id, agent in agents.items():
        textconsole.print(f"[green]{agent_id}[/]: {agent['name']}")
        if ctx.obj["VERBOSE"]:
            textconsole.print(f"    {agent['description']}")
            textconsole.print(f"    [yellow]Developer[/]: {agent['developer']}")
            if "moreInfo" in agent and agent["moreInfo"]:
                textconsole.print(f"    [yellow]More info[/]: {agent['moreInfo']}")
            textconsole.print("")


@cli.group(help="Session-related commands.")
def sessions():
    pass


@sessions.command("list", help="List sessions.")
@click.pass_context
def list_sessions(ctx):
    client = ctx.obj["CLIENT"]
    session_ids = client.sessions()
    for session_id in session_ids:
        textconsole.print(f"[green]{session_id}[/]")


@sessions.command("show", help="Show session.")
@click.pass_context
@click.argument("session_id")
def show_session(ctx, session_id: str):
    llamalabs_api_url = ctx.obj["LLAMALABS_API_URL"]
    client = llamalabs.LlamaLabsClient(api_url=llamalabs_api_url)
    session = client.get_session(session_id)
    messages = session.get_messages()
    textconsole.print(messages)


@sessions.command("embeds", help="Show embeds in a session.")
@click.pass_context
@click.argument("session_id")
def embeds(ctx, session_id: str):
    llamalabs_api_url = ctx.obj["LLAMALABS_API_URL"]
    client = llamalabs.LlamaLabsClient(api_url=llamalabs_api_url)
    session = client.get_session(session_id)
    embeds = session.get_embeds()
    textconsole.print(embeds)


if __name__ == "__main__":
    cli()
