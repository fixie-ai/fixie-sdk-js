import webbrowser
from typing import Optional

import click
from oauth2_client import credentials_manager
import secrets

# Fixie CLI Client ID.
# CLIENT_ID = "yNQGgbclvinYau20mS6gtE6nbRprbBUM"  # fixie-cli app client id
# CLIENT_ID = "wV1l8u48os7kX4FpZAO8ORNAYv07nVS9"  # dev client id
CLIENT_ID = "3fXy1EoOPLN9OmFKGKLtUxaLFVZl5lSB"  # Prod client id
# Scopes to request access for.
SCOPES = ["openid", "profile", "email"]
# The authorization URL that users click on.
AUTHORIZE_SERVICE = "https://auth.fixie.ai/authorize"
# The token exchange service that we use internally.
TOKEN_SERVICE = "https://auth.fixie.ai/oauth/token"
# The ServiceInformation object that encapsulates all above.
SERVICE_INFORMATION = credentials_manager.ServiceInformation(
    AUTHORIZE_SERVICE,
    TOKEN_SERVICE,
    CLIENT_ID,
    None,
    SCOPES,
)
# We will try listening on the first open port from this list.
REDIRECT_PORTS = [8212, 8562, 8452, 8523, 8027]


def oauth_flow() -> Optional[str]:
    """Runs an interactive authorization flow with the user, and returns fixie_api_token
    if successful."""
    manager = credentials_manager.CredentialManager(SERVICE_INFORMATION)

    url: Optional[str] = None
    errors = []

    for port in REDIRECT_PORTS:
        try:
            redirect_uri = f"http://localhost:{port}"
            url = manager.init_authorize_code_process(
                redirect_uri,
                secrets.token_urlsafe(),
            )
            break
        except OSError as err:
            # Port is busy. We'll try the next port.
            errors.append(err)
            pass

    if url is None:
        click.secho(
            f"Could not bind to any of the selected ports {REDIRECT_PORTS}. "
            f"Please check these ports and whether the fixie CLI has the right "
            "permissions to bind to a port. If need help, don't hesitate to contact "
            f"us developers@fixie.ai. Please send this error message: :\n{errors}",
            fg="red",
        )
        return None

    success = webbrowser.open(url)
    if success:
        click.echo("Your browser has been opened to visit:")
        click.echo()
        click.echo(f"    {url}")
    else:
        click.echo("Open this link on your browser to continue:")
        click.echo()
        click.echo(f"    {url}")

    # Now we wait to receive an oauth code at the redirect uri.
    code = manager.wait_and_terminate_authorize_code_process()
    # Now we exchange the code for a fixie access token.
    manager.init_with_authorize_code(redirect_uri, code)
    # Now get an API KEY with the access token.
    response = manager.get("https://app.fixie.ai/profile")
    print(response.content.decode())
    import pdb; pdb.set_trace()
    return manager._access_token
