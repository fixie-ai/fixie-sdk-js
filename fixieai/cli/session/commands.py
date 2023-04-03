import click

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
@click.pass_context
def new_session(ctx, agent, web, message):
    client = ctx.obj.client
    session = client.create_session(agent)
    if web:
        click.launch(session.session_url)
        return

    c = console.Console(client, session=session)
    c.run(message)


@session.command("open", help="Opens a session.")
@click.argument("session_id")
@web_option
@click.pass_context
def open_session(ctx, web, session_id: str):
    client = ctx.obj.client
    session = client.get_session(session_id)
    if web:
        click.launch(session.session_url)
        return

    c = console.Console(client, session=session)
    c.run()


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
    client = ctx.obj.client
    session = client.create_session(agent)
    if verbose:
        click.secho(f"Session ID: ", nl=False)
        click.secho(f"{session.session_id}", fg="green")
        click.secho(f"Session URL: ", nl=False)
        click.secho(f"{session.session_url}", fg="green")

    if web:
        click.launch(session.session_url)
        return

    response = session.query(message)

    print(response)
    if not keep:
        if verbose:
            click.echo(f"Deleting session ", nl=False)
            click.secho(f"{session.session_id}", fg="green")
        session.delete_session()
