import json
import subprocess


class Tunnel:
    """Start an Internet-accessible tunnel to the Agent running at the given host:port.

    Returns a generator that yields public URLs on which the Agent can be contacted.

    Shuts down the tunnel when the context manager exits.
    """

    def __init__(self, port: int):
        self._port = port

    def __enter__(self):
        self._proc = subprocess.Popen(
            [
                "ssh",
                "-R",
                # N.B. 127.0.0.1 must be used on Windows (not localhost or 0.0.0.0)
                f"80:127.0.0.1:{self._port}",
                "-o",
                # Need to send keepalives to prevent the connection from getting chopped
                # (see https://localhost.run/docs/faq#my-connection-is-unstable-tunnels-go-down-often)
                "ServerAliveInterval=59",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "nokey@localhost.run",
                "--",
                "--output=json",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
        )

        def _gen():
            while True:
                assert self._proc.stdout is not None
                line = self._proc.stdout.readline()
                if not line:
                    break
                try:
                    parsed = json.loads(line)
                    if "address" in parsed:
                        yield f"https://{parsed['address']}"
                except:
                    pass

        return _gen()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._proc.terminate()
        self._proc.wait()
