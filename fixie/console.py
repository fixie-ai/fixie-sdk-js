#!/usr/bin/env python3


import prompt_toolkit
import requests
import rich.console as rich_console

import fixie

HISTORY_FILE = "history.txt"

console = rich_console.Console()


class Console:
    """A simple console interface for Fixie."""

    def __init__(
        self,
        client: fixie.FixieClient,
        history_file: str = HISTORY_FILE,
    ):
        self._client = client
        self._history_file = history_file
        self._response_index = 0

    def run(self) -> None:
        """Run the console application."""

        console.print("[blue]Welcome to Fixie!")
        console.print(f"Connected to: {self._client.session_url}")
        while True:
            in_text = prompt_toolkit.prompt(
                "🚲❯ ",
                history=prompt_toolkit.history.FileHistory(self._history_file),
                auto_suggest=prompt_toolkit.auto_suggest.AutoSuggestFromHistory(),
            )
            self._query(in_text)

    def _query(self, in_text: str) -> None:
        with console.status("Working...", spinner="bouncingBall"):
            try:
                self._response_index += 1
                for response, sent_by, type in self._client.run(in_text):
                    if type != "response":
                        console.print(f"   [dim]@{sent_by}: {response}[/]")
                    else:
                        console.print(f"{self._response_index}❯ {response}")
            except requests.exceptions.HTTPError as e:
                console.print(f"🚨 {e}")
                return
