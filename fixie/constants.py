import os

FIXIE_API_URL = os.getenv("FIXIE_API_URL", "https://app.fixie.ai")
FIXIE_API_KEY = os.getenv("FIXIE_API_KEY")

FIXIE_USER_STORAGE_URL = f"{FIXIE_API_URL}/api/userstorage"
