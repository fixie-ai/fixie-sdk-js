#!/usr/bin/env python3

from typing import Optional

import click
import pkg_resources
import requests
from packaging import version

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


def get_installed_version(package_name: str) -> Optional[str]:
    try:
        # Get the distribution object for the specified package
        distribution = pkg_resources.get_distribution(package_name)
        # Get the version of the installed package
        installed_version = distribution.version
        return str(installed_version)
    except pkg_resources.DistributionNotFound:
        # Handle the case where the package is not found
        return None


def check_for_update(package_name: str):
    installed_version = get_installed_version(package_name)
    if not installed_version:
        return
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=3)
        response.raise_for_status()
    except Exception as e:
        click.secho(f"An error occurred while checking for updates: {e}", fg="yellow")
        return

    package_info = response.json()
    latest_version = package_info["info"]["version"]
    if version.parse(installed_version) < version.parse(latest_version):
        click.secho(
            f"🦊 A newer version of {package_name} is available: {latest_version}",
            fg="green",
        )

        click.secho(f"You are currently using version {installed_version}", fg="yellow")
        click.secho(f"You can upgrade using:", fg="yellow")
        click.secho(f"   pip install --upgrade {package_name}\n\n", fg="blue")


if __name__ == "__main__":
    check_for_update("fixieai")
    fixie()
