import click
from gql.transport import exceptions as gql_exceptions

from fixieai.cli.auth import oauth_flow
from fixieai.cli.auth import user_config
from fixieai.client import client


def validate_not_authed(ctx, param, force):
    """Click option callback for "fixie auth --force" that validates user is not
    authenticated if "--force" is not set."""
    if force:
        # --force is set
        return
    try:
        auth_token = user_config.load_config().auth_token
        if auth_token is not None:
            username = _get_username(auth_token)
            click.echo("Already authenticated as ", nl=False)
            click.secho(username, fg="green", nl=False, bold=True)
            click.echo(". Set --force to force re-authentication.")
            ctx.exit()
    except (FileNotFoundError, gql_exceptions.TransportQueryError):
        pass


def _get_username(auth_token: str) -> str:
    """Gets the username for an auth token."""
    return client.FixieClient(auth_token).get_current_username()


@click.command("auth", help="Authorizes `fixie` to access Fixie platform.")
@click.option(
    "--force",
    is_flag=True,
    help="Forces authentication, even if the user is authenticated.",
    callback=validate_not_authed,
    expose_value=False,
)
def auth():
    fixie_auth_token = oauth_flow.oauth_flow()
    try:
        config = user_config.load_config()
    except FileNotFoundError:
        config = user_config.UserConfig()

    config.auth_token = fixie_auth_token
    user_config.save_config(config)

    username = _get_username(fixie_auth_token)
    click.secho("Success! You're authenticated as ", fg="green", bold=True, nl=False)
    click.secho(username, fg="magenta", nl=False, bold=True)
    click.secho(".")


@click.command("user", help="Displays information on the authenticated user.")
@click.pass_context
def user(ctx):
    current_user = ctx.obj.client.get_current_user()
    click.secho("You are authenticated to ", nl=False)
    click.secho(ctx.obj.client.url, fg="yellow", nl=False)
    click.secho(" as:")
    for key, value in current_user.items():
        click.secho(key, fg="green", nl=False)
        click.echo(f": {value}")
