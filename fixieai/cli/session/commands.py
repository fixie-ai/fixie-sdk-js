import click

from fixieai.cli.session import console


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
@click.argument("message", required=False)
@click.pass_context
def new_session(ctx, message):
    client = ctx.obj.client
    c = console.Console(client)
    c.run(message)


@session.command("open", help="Opens a session.")
@click.pass_context
@click.argument("session_id")
def open_session(ctx, session_id: str):
    client = ctx.obj.client
    selected_session = client.get_session(session_id)
    c = console.Console(client, session=selected_session)
    c.run()
