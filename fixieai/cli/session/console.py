import prompt_toolkit
import requests
import rich.console as rich_console

from fixieai import FixieClient

HISTORY_FILE = "history.txt"
textconsole = rich_console.Console()


class Console:
    """A simple console interface for Fixie."""

    def __init__(
        self,
        client: FixieClient,
        history_file: str = HISTORY_FILE,
    ):
        self._client = client
        self._session = client.create_session()
        self._history_file = history_file
        self._response_index = 0

    def run(self) -> None:
        """Run the console application."""

        textconsole.print("[blue]Welcome to Fixie!")
        textconsole.print(f"Connected to: {self._session.session_url}")
        while True:
            in_text = prompt_toolkit.prompt(
                "fixie 🚲❯ ",
                history=prompt_toolkit.history.FileHistory(self._history_file),
                auto_suggest=prompt_toolkit.auto_suggest.AutoSuggestFromHistory(),
            )
            self._query(in_text)

    def _query(self, in_text: str) -> None:
        with textconsole.status("Working...", spinner="bouncingBall"):
            try:
                self._response_index += 1
                for message in self._session.run(in_text):
                    if message["type"] != "response":
                        textconsole.print(
                            f"   [dim]@{message['sentBy']['handle']}: {message['text']}[/]"
                        )
                    else:
                        textconsole.print(f"{self._response_index}❯ {message['text']}")
            except requests.exceptions.HTTPError as e:
                textconsole.print(f"🚨 {e}")
                return
