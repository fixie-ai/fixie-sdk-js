"""This file holds some configuration constants, including URL to Fixie services,
and your Fixie API key."""

import os

import yaml

# Base Fixie platform URL.
FIXIE_API_URL = os.getenv("FIXIE_API_URL", "https://app.fixie.ai")
# Path to fixie config file.
FIXIE_CONFIG_PATH = os.getenv(
    "FIXIE_CONFIG_PATH",
    os.path.expanduser("~/.config/fixie/config.yaml"),
)

# Fixie's UserStorage service URL.
FIXIE_USER_STORAGE_URL = f"{FIXIE_API_URL}/api/userstorage"
# Fixie's refresh endpoint. It will be pinged when your agent comes alive.
FIXIE_REFRESH_URL = f"{FIXIE_API_URL}/api/refresh"
# Fixie's OAuth redirect endpoint. Tokens sent to this endpoint will be redirected back
# to your agent.
FIXIE_OAUTH_REDIRECT_URL = f"{FIXIE_API_URL}/oauth"

FIXIE_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEANcDOXX9KOKx64wNUuq9oyGKfj5lZJjM/0Qgj/A55PTw=
-----END PUBLIC KEY-----"""

FIXIE_AGENT_API_AUDIENCE = "https://app.fixie.ai/api"


def fixie_api_key() -> str:
    if os.getenv("FIXIE_API_KEY"):
        return os.getenv("FIXIE_API_KEY")
    try:
        with open(FIXIE_CONFIG_PATH) as fp:
            return yaml.safe_load(fp)["fixie_api_key"]
    except (FileNotFoundError, KeyError):
        raise ValueError(
            "User is not authenticated. Run 'fixie auth' to authenticate, or set the "
            "FIXIE_API_KEY environment variable, which can be obtained from your "
            "profile page at https://app.fixie.ai/profile"
        )


def is_authenticated() -> bool:
    try:
        fixie_api_key()
    except ValueError:
        return False
    else:
        return True
