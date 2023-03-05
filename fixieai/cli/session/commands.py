import click

from fixieai.cli.session import console


@click.group(help="Session-related commands.")
def session():
    pass


@session.command("list", help="Lists sessions.")
@click.pass_context
def list_sessions(ctx):
    client = ctx.obj["CLIENT"]
    session_ids = client.get_sessions()
    for session_id in session_ids:
        click.secho(f"{session_id}", fg="green")


@session.command("new", help="Creates a new session and opens it.")
@click.pass_context
def new_session(ctx):
    client = ctx.obj["CLIENT"]
    c = console.Console(client)
    c.run()


@session.command("open", help="Opens a session.")
@click.pass_context
@click.argument("session_id")
def open_session(ctx, session_id: str):
    client = ctx.obj["CLIENT"]
    session = client.get_session(session_id)
    messages = session.get_messages()
    click.echo(messages)
