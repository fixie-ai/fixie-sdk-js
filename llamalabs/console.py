#!/usr/bin/env python3


import prompt_toolkit
import requests
import rich.console as rich_console

import llamalabs

HISTORY_FILE = "history.txt"

console = rich_console.Console()


class Console:
    """A simple console interface for Llama Labs."""

    def __init__(
        self,
        client: llamalabs.LlamaLabsClient,
        history_file: str = HISTORY_FILE,
    ):
        self._client = client
        self._session = client.create_session()
        self._history_file = history_file
        self._response_index = 0

    def run(self) -> None:
        """Run the console application."""

        console.print("[blue]Welcome to Llama Labs!")
        console.print(f"Connected to: {self._session.session_url}")
        while True:
            in_text = prompt_toolkit.prompt(
                "🦙❯ ",
                history=prompt_toolkit.history.FileHistory(self._history_file),
                auto_suggest=prompt_toolkit.auto_suggest.AutoSuggestFromHistory(),
            )
            self._query(in_text)

    def _query(self, in_text: str) -> None:
        with console.status("Working...", spinner="bouncingBall"):
            try:
                self._response_index += 1
                for message in self._session.run(in_text):
                    if message["type"] != "response":
                        console.print(
                            f"   [dim]@{message['sentBy']}: {message['text']}[/]"
                        )
                    else:
                        console.print(f"{self._response_index}❯ {message['text']}")
            except requests.exceptions.HTTPError as e:
                console.print(f"🚨 {e}")
                return
