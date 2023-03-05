import webbrowser
import socket
from typing import Optional

import click
from oauth2_client import credentials_manager
import secrets

from fixieai import constants

# Fixie CLI Client ID.
CLIENT_ID = "II4FM6ToxVwSKB6DW1r114AKAuSnuZEgYehEBB-5WQA"
# Scopes to request access for.
SCOPES = ["fixie-api-key"]
# The authorization URL that users click on.
AUTHORIZE_SERVICE = f"{constants.FIXIE_API_URL}/authorize"
# The token exchange service that we use internally.
TOKEN_SERVICE = f"{constants.FIXIE_API_URL}/oauth/token"
# The ServiceInformation object that encapsulates all above.
SERVICE_INFORMATION = credentials_manager.ServiceInformation(
    AUTHORIZE_SERVICE,
    TOKEN_SERVICE,
    CLIENT_ID,
    None,
    SCOPES,
)


def oauth_flow() -> Optional[str]:
    """Runs an interactive authorization flow with the user, and returns fixie_api_token
    if successful."""
    manager = credentials_manager.CredentialManager(SERVICE_INFORMATION)

    port = find_free_port()
    redirect_uri = f"http://localhost:{port}"
    state = secrets.token_urlsafe()
    url = manager.init_authorize_code_process(
        redirect_uri,
        state,
    )

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
    return manager._access_token


def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]
