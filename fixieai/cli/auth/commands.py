import click

from fixieai.cli.auth import oauth_flow
from fixieai.cli.auth import user_config


def validate_not_authed(ctx, param, force):
    """Click option callback for "fixie auth --force" that validates user is not
    authenticated if "--force" is not set."""
    if force:
        # --force is set
        return
    try:
        config = user_config.load_config()
        if config.fixie_api_key is not None:
            click.echo("Already authenticated. Set --force to force re-authentication.")
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
