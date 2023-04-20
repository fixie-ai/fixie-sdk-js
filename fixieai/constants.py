"""This file holds some configuration constants, including URL to Fixie services,
and your Fixie API key."""

import os

# Base Fixie platform URL.
FIXIE_API_URL = os.getenv("FIXIE_API_URL", "https://app.fixie.ai")
# Path to fixie config file.
FIXIE_CONFIG_PATH = os.getenv(
    "FIXIE_CONFIG_PATH",
    os.path.expanduser("~/.config/fixie/config.yaml"),
)

# Fixie's GraphQL URL.
FIXIE_GRAPHQL_URL = f"{FIXIE_API_URL}/graphql"
# Fixie's UserStorage service URL.
FIXIE_USER_STORAGE_URL = f"{FIXIE_API_URL}/api/userstorage"
# Fixie's refresh endpoint. It will be pinged when your agent comes alive.
FIXIE_REFRESH_URL = f"{FIXIE_API_URL}/api/refresh"
# Fixie's OAuth redirect endpoint. Tokens sent to this endpoint will be redirected back
# to your agent.
FIXIE_OAUTH_REDIRECT_URL = f"{FIXIE_API_URL}/oauth"
# Fixie's deployments service URL.
FIXIE_DEPLOYMENT_URL = f"{FIXIE_API_URL}/api/deployments"
# Fixie's JWKS URL.
FIXIE_JWKS_URL = f"{FIXIE_API_URL}/.well-known/jwks.json"
# Fixie's OpenAI Proxy URL.
FIXIE_OPENAI_PROXY_URL = f"{FIXIE_API_URL}/api/openai-proxy/v1"
# Valid audiences for Fixie's query JWTs.
FIXIE_AGENT_API_AUDIENCES = ["https://app.fixie.ai/api", "https://app.dev.fixie.ai/api"]


def fixie_api_key() -> str:
    """Returns authenticated user's fixie auth token.

    User may authenticate via `fixie auth`, or by setting FIXIE_API_KEY environment
    variable to override any previous authentication.

    If user is not authenticated and FIXIE_API_KEY is not set, a PermissionError is
    raised.
    """
    if "FIXIE_API_KEY" in os.environ:
        return os.environ["FIXIE_API_KEY"]
    try:
        from fixieai.cli.auth import user_config

        auth_token = user_config.load_config().auth_token
        assert isinstance(auth_token, str)
        return auth_token
    except (FileNotFoundError, KeyError, AssertionError):
        raise PermissionError(
            "User is not authenticated. Run 'fixie auth' to authenticate, or set the "
            "FIXIE_API_KEY environment variable, which can be obtained from your "
            "profile page at https://app.fixie.ai/profile"
        )


def is_authenticated() -> bool:
    """Returns true if the current user is authenticated."""
    try:
        fixie_api_key()
    except PermissionError:
        return False
    else:
        return True
