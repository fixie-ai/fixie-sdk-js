#!/usr/bin/env python3


import click
import rich.console as rich_console

import fixie.client as fixie_client

console = rich_console.Console()


@click.group()
@click.option(
    "--fixie_api_host",
    help="Fixie API host. Defaults to the value of the FIXIE_API_HOST env var, or `app.fixie.ai` if that is unset.",
)
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def cli(ctx, fixie_api_host, verbose):
    ctx.ensure_object(dict)
    client = fixie_client.FixieClient(api_host=fixie_api_host)
    ctx.obj["CLIENT"] = client
    ctx.obj["VERBOSE"] = verbose


@cli.group(help="Agent-related commands.")
def agents():
    pass


@agents.command("list", help="List agents.")
@click.pass_context
def list_agents(ctx):
    client = ctx.obj["CLIENT"]
    agents = client.agents()
    for agent_id, agent in agents.items():
        console.print(f"[green]{agent_id}[/]: {agent['name']}")
        if ctx.obj["VERBOSE"]:
            console.print(f"    {agent['description']}")
            console.print(f"    [yellow]Developer[/]: {agent['developer']}")
            if "moreInfo" in agent and agent["moreInfo"]:
                console.print(f"    [yellow]More info[/]: {agent['moreInfo']}")
            console.print("")


@cli.group(help="Playground-related commands.")
def playgrounds():
    pass


@playgrounds.command("list", help="List playgrounds.")
@click.pass_context
def list_playgrounds(ctx):
    client = ctx.obj["CLIENT"]
    playgrounds = client.playgrounds()
    for handle, playground in playgrounds.items():
        console.print(f"[green]{handle}[/]: {playground['name']}")
        if ctx.obj["VERBOSE"]:
            console.print(f"    {playground['description']}")
            console.print(f"    [yellow]Owner[/]: {playground['owner']}")
            console.print("")


@playgrounds.command("show", help="Show playground.")
@click.pass_context
@click.argument("handle")
def show_playground(ctx, handle: str):
    client = ctx.obj["CLIENT"]
    playground = client.get_playground(handle)
    console.print(playground)


if __name__ == "__main__":
    cli()
