import click

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
        config = user_config.load_config()
        if config.fixie_api_key is not None:
            username = _get_username(config.fixie_api_key)
            click.echo("Already authenticated as ", nl=False)
            click.secho(username, fg="green", nl=False, bold=True)
            click.echo(". Set --force to force re-authentication.")
            ctx.exit()
    except FileNotFoundError:
        pass


@click.command("auth", help="Authorizes `fixie` to access Fixie platform.")
@click.option(
    "--force",
    is_flag=True,
    help="Forces authentication, even if the user is authenticated.",
    callback=validate_not_authed,
    expose_value=False,
)
def auth():
    fixie_api_token = oauth_flow.oauth_flow()
    try:
        config = user_config.load_config()
    except FileNotFoundError:
        config = user_config.UserConfig()

    config.fixie_api_key = fixie_api_token
    user_config.save_config(config)

    username = _get_username(fixie_api_token)
    click.secho("Success! You're authenticated as ", fg="green", bold=True, nl=False)
    click.secho(username, fg="magenta", nl=False, bold=True)
    click.secho(".")


def _get_username(api_key: str) -> str:
    """Gets the username for an api_key."""
    return client.FixieClient(api_key).get_current_username()
