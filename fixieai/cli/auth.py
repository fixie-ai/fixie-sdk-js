import os
import secrets
import socket
from typing import Optional
import urllib.parse

from fixieai import constants

# Fixie CLI Client ID.
CLIENT_ID = "yNQGgbclvinYau20mS6gtE6nbRprbBUM"
# We will try listening on these ports, whichever is open.
REDIRECT_PORTS = [8212, 8562, 8452, 8523, 8027]
# Scopes to request access for.
SCOPES = ["openid"]
# The auth URL users should click on
AUTH_URL = "https://dev-ce7lcdzmwxrdx6cb.us.auth0.com/authorize"
# Maximum amount of data we expect to receive from redirect callback.
MAX_BUFF_SIZE = 4096  # 4 KB


def authentication_flow():
    s = socket.socket()
    bound_port: Optional[int] = None
    errors = []
    for port in REDIRECT_PORTS:
        try:
            s.bind(("localhost", port))
            bound_port = port
            break
        except socket.error as e:
            errors.append(e)
            pass
    if bound_port is None:
        raise RuntimeError(
            f"Could not bind to any of the selected ports {REDIRECT_PORTS}. "
            f"Please check these ports and whether the fixie CLI has the right "
            "permissions to bind to a port. If need help, dont' hesitate to contact "
            f"developers@fixie.ai and pass them this error message:\n{errors}"
        )

    auth_state = secrets.token_urlsafe()
    data = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "scope": " ".join(SCOPES),
            "state": auth_state,
            "redirect_uri": f"http://localhost:{bound_port}",
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(data)

    print(url)

    # Start listening on the port
    s.listen(1)
    conn, addr = s.accept()
    data = conn.recv(MAX_BUFF_SIZE)

    conn.send("Success!")
    import pdb; pdb.set_trace()
