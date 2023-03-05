"""This file holds some configuration constants, including URL to Fixie services,
and your Fixie API key."""

import os

# Base Fixie platform URL.
FIXIE_API_URL = os.getenv("FIXIE_API_URL", "https://app.fixie.ai")
# Your Fixie API key, set from environment variables.
FIXIE_API_KEY = os.getenv("FIXIE_API_KEY")

# Fixie's UserStorage service URL.
FIXIE_USER_STORAGE_URL = f"{FIXIE_API_URL}/api/userstorage"
# Fixie's refresh endpoint. It will be pinged when your agent comes alive.
FIXIE_REFRESH_URL = f"{FIXIE_API_URL}/api/refresh"
# Fixie's OAuth redirect endpoint. Tokens sent to this endpoint will be redirected back
# to your agent.
FIXIE_OAUTH_REDIRECT_URL = f"{FIXIE_API_URL}/oauth"
# Fixie's JWKS URL.
FIXIE_JWKS_URL = f"{FIXIE_API_URL}/.well-known/jwks.json"

# The audience for Fixie's query JWTs.
FIXIE_AGENT_API_AUDIENCE = "https://app.fixie.ai/api"
