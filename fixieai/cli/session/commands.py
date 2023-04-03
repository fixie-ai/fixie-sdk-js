from typing import Optional

import click

from fixieai import FixieClient
from fixieai.cli.session import console


def validate_agent_exists(ctx, param, agent_id):
    if agent_id is not None:
        client = ctx.obj.client
        agent = client.get_agent(agent_id)
        if not agent.valid:
            raise click.BadParameter(f"Agent {agent_id} does not exist")
    return agent_id


@click.group(help="Session-related commands.")
def session():
    pass


@session.command("list", help="Lists sessions.")
@click.pass_context
def list_sessions(ctx):
    client = ctx.obj.client
    session_ids = client.get_sessions()
    for session_id in session_ids:
        click.secho(f"{session_id}", fg="green")


def web_option(func):
    return click.option(
        "--web",
        is_flag=True,
        help="Open the session in the web interface.",
    )(func)


def run_session(
    client: FixieClient,
    session_id: Optional[str] = None,
    agent: Optional[str] = None,
    message: Optional[str] = None,
    use_console: bool = False,
    web: bool = False,
    keep: bool = False,
    verbose: bool = False,
):
    """Runs a session.

    Args:
        client: The FixieClient instance.
        session_id: The ID of the session to use. If not provided, a new session is created.
        agent: The agent to use for the session.
        message: The message to send to the session.
        use_console: Whether to run the session in the console.
        web: Whether to open the session in the web interface.
        keep: Whether to keep the session after it is finished.
        verbose: Whether to print verbose output.
    """
    if session_id is not None:
        session = client.get_session(session_id)
    else:
        session = client.create_session(agent)
    if verbose:
        click.secho(f"Session ID: ", nl=False)
        click.secho(f"{session.session_id}", fg="green")
        click.secho(f"Session URL: ", nl=False)
        click.secho(f"{session.session_url}", fg="green")

    if web:
        click.launch(session.session_url)
        return
    if use_console:
        c = console.Console(client, session=session)
        c.run(message)
    else:
        if message:
            response = session.query(message)
            print(response)
        if web:
            if keep:
                click.secho(
                    "Warning: --keep is ignored when --web is specified.",
                    fg="yellow",
                )
            click.launch(session.session_url)
            return
        elif not message:
            raise click.BadParameter(
                "You must specify either --console, --web, or a query message"
            )

    if not keep:
        if verbose:
            click.echo(f"Deleting session ", nl=False)
            click.secho(f"{session.session_id}", fg="green")
        session.delete_session()


@session.command("new", help="Creates a new session and opens it.")
@click.argument("message", required=False)
@web_option
@click.option(
    "-a",
    "--agent",
    required=False,
    callback=validate_agent_exists,
    help="A specific agent to talk to. If unset, `fixie` is used.",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def new_session(ctx, agent, web, message, verbose):
    run_session(ctx.obj.client, agent=agent, message=message, web=web, use_console=True)


@session.command("open", help="Opens a session.")
@click.argument("session_id", required=True)
@click.argument("message", required=False)
@web_option
@click.option(
    "-a",
    "--agent",
    required=False,
    callback=validate_agent_exists,
    help="A specific agent to talk to. If unset, `fixie` is used.",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def open_session(ctx, session_id: str, web, agent, message, verbose):
    run_session(
        ctx.obj.client,
        session_id=session_id,
        agent=agent,
        message=message,
        web=web,
        use_console=True,
    )


@session.command("query", help="Runs a single query and exit.")
@click.argument("message", required=True)
@web_option
@click.option("--keep", is_flag=True, help="Do not delete the session after use.")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.option(
    "-a",
    "--agent",
    required=False,
    callback=validate_agent_exists,
    help="A specific agent to talk to. If unset, `fixie` is used.",
)
@click.pass_context
def query(ctx, agent, web, keep, verbose, message):
    run_session(
        ctx.obj.client,
        agent=agent,
        message=message,
        web=web,
        keep=keep,
        verbose=verbose,
        use_console=False,
    )
