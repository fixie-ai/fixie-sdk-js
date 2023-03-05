#!/usr/bin/env python3

import click

import fixieai
from fixieai.cli.agent import commands as agent_commands
from fixieai.cli.session import commands as session_commands


@click.group()
@click.pass_context
def fixie(ctx):
    """Command-line interface to the Fixie platform."""
    ctx.ensure_object(dict)
    client = fixieai.FixieClient()
    ctx.obj["CLIENT"] = client


# Add subcommands
fixie.add_command(agent_commands.agent)
fixie.add_command(session_commands.session)

# Add aliases for commonly used paths
fixie.add_command(agent_commands.init_agent, "init")
fixie.add_command(session_commands.new_session, "console")


if __name__ == "__main__":
    fixie()
