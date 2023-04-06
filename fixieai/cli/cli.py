#!/usr/bin/env python3

from typing import Optional

import click

import fixieai
from fixieai import constants
from fixieai.cli.agent import commands as agent_commands
from fixieai.cli.auth import commands as auth_commands
from fixieai.cli.session import commands as session_commands


class CliContext:
    def __init__(self):
        self._client: Optional[fixieai.FixieClient] = None

    @property
    def client(self) -> fixieai.FixieClient:
        if self._client is None:
            if constants.is_authenticated():
                self._client = fixieai.FixieClient()
            else:
                click.secho(
                    "User is not authenticated. Run 'fixie auth' to authenticate, or "
                    "set the FIXIE_API_KEY environment variable, which can be obtained"
                    " from your profile page at https://app.fixie.ai/profile",
                    fg="red",
                )
                raise click.exceptions.Exit(11)
        return self._client


@click.group()
@click.pass_context
def fixie(ctx):
    """Command-line interface to the Fixie platform."""
    ctx.ensure_object(CliContext)


# Add subcommands
fixie.add_command(agent_commands.agent)
fixie.add_command(auth_commands.auth)
fixie.add_command(session_commands.session)
fixie.add_command(auth_commands.user)

# Add aliases for commonly used paths
fixie.add_command(agent_commands.init_agent, "init")
fixie.add_command(agent_commands.deploy, "deploy")
fixie.add_command(agent_commands.serve, "serve")
fixie.add_command(agent_commands.publish, "publish")
fixie.add_command(agent_commands.unpublish, "unpublish")
fixie.add_command(session_commands.new_session, "console")
fixie.add_command(session_commands.query, "query")


if __name__ == "__main__":
    fixie()
