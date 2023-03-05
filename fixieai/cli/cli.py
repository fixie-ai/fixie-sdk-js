#!/usr/bin/env python3

import click
import rich.console as rich_console

import fixieai
from fixieai.cli.agent import commands as agent_commands
from fixieai.cli.session import commands as session_commands

textconsole = rich_console.Console()


@click.group()
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def fixie(ctx, verbose):
    """Command-line interface to the Fixie platform."""
    ctx.ensure_object(dict)
    client = fixieai.FixieClient()
    ctx.obj["CLIENT"] = client
    ctx.obj["VERBOSE"] = verbose


fixie.add_command(agent_commands.agent)
fixie.add_command(session_commands.sessions)


if __name__ == "__main__":
    fixie()
