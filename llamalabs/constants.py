import os

LLAMALABS_API_URL = os.getenv("LLAMALABS_API_URL", "https://app.llamalabs.ai")
LLAMALABS_API_KEY = os.getenv("LLAMALABS_API_KEY")

LLAMALABS_USER_STORAGE_URL = f"{LLAMALABS_API_URL}/api/userstorage"
