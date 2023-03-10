import click

from fixieai.cli.session import console


def validate_agent_exists(ctx, param, agent_id):
    client = ctx.obj.client
    agent = client.get_agent(agent_id)
    if not agent.valid:
        click.echo(f"Agent {agent_id} not found.")
        ctx.exit(1)


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


@session.command("new", help="Creates a new session and opens it.")
@click.option(
    "-a",
    "--agent",
    required=False,
    callback=validate_agent_exists,
    help="A specific agent to talk to. If unset, `fixie` is used.",
)
@click.argument("message", required=False)
@click.pass_context
def new_session(ctx, agent, message):
    client = ctx.obj.client
    c = console.Console(client, agent)
    c.run(message)


@session.command("open", help="Opens a session.")
@click.pass_context
@click.argument("session_id")
def open_session(ctx, session_id: str):
    client = ctx.obj.client
    session = client.get_session(session_id)
    messages = session.get_messages()
    click.echo(messages)
