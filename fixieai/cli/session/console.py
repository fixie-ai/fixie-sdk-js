import io
import os.path
import re
from typing import Any, Dict, List, Optional

import prompt_toolkit
import prompt_toolkit.history
import requests
from PIL import Image
from rich import console as rich_console
from rich.markdown import Markdown

from fixieai import FixieClient
from fixieai.client.client import Session

HISTORY_FILE = "~/.config/fixie/history.log"
textconsole = rich_console.Console(soft_wrap=True)
PROMPT = "fixie 🦊❯ "


class Console:
    """A simple console interface for Fixie."""

    def __init__(
        self,
        client: FixieClient,
        session: Session,
        history_file: str = HISTORY_FILE,
    ):
        self._client = client
        self._session = session
        history_file = os.path.expanduser(history_file)
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        self._history_file = history_file
        self._response_index = 0

    def run(
        self,
        initial_message: Optional[str] = None,
    ) -> None:
        """Run the console application."""

        textconsole.print("[blue]Welcome to Fixie!")
        textconsole.print(f"Connected to: {self._session.session_url}")

        # Show what's already in the session thus far.
        for message in self._session.get_messages_since_last_time():
            self._show_message(message, show_user_message=True)

        history = prompt_toolkit.history.FileHistory(self._history_file)
        if initial_message:
            prompt_toolkit.print_formatted_text(f"{PROMPT}{initial_message}")
            history.append_string(initial_message)
            self._query(initial_message)

        while True:
            in_text = prompt_toolkit.prompt(
                PROMPT,
                history=history,
                auto_suggest=prompt_toolkit.auto_suggest.AutoSuggestFromHistory(),
            )
            self._query(in_text)

    def _query(self, in_text: str) -> None:
        with textconsole.status("Working...", spinner="bouncingBall"):
            try:
                for message in self._session.run(in_text):
                    self._show_message(message)
            except requests.exceptions.HTTPError as e:
                textconsole.print(f"🚨 {e}")
                return

    def _show_message(self, message: Dict[str, Any], show_user_message: bool = False):
        """Shows a message dict from FixieClient.

        If show_user_message is set, the user messages are also printed with the PROMPT.
        This option is useful for showing previous messages in the chat when connecting
        to a session.
        """
        sender_handle = (
            message["sentBy"]["handle"] if message["sentBy"] else "<unknown>"
        )
        message_text = message["text"]

        if message["type"] == "query" and sender_handle == "user":
            if show_user_message:
                textconsole.print(Markdown(PROMPT + message_text))
        elif message["type"] != "response":
            textconsole.print(
                Markdown(f"   @{sender_handle}: " + message_text, style="dim")
            )
        else:
            self._response_index += 1
            textconsole.print(Markdown(f"{self._response_index}❯ " + message_text))
            self._show_embeds(message["text"])

    def _show_embeds(self, message: str):
        """Shows embeds referenced in `message_text`."""
        # Check embed references in message (denoted by #id).
        embed_ids = _extract_embed_refs(message)
        if not embed_ids:
            return
        # Get a dict of all embed_id -> embeds in the session.
        embeds = {
            embed_dict["key"]: embed_dict["embed"]
            for embed_dict in self._session.get_embeds()
        }
        # Show what we can find.
        for embed_id in embed_ids:
            if embed_id not in embeds:
                textconsole.print(
                    f"   [dim]embed #{embed_id} not found in session[/]", style="red"
                )
                continue
            _show_embed(
                embeds[embed_id]["url"],
                embeds[embed_id]["contentType"],
            )


def _extract_embed_refs(message: str) -> List[int]:
    """Returns a list of embed ids referenced in `message_text`."""
    embed_refs = []
    odd_number_of_sharps = r"(?<!#)(##)*#(?!#)"
    for match in re.finditer(odd_number_of_sharps + r"(?P<embed_num>\d+)", message):
        embed_refs.append(int(match.group("embed_num")))
    return embed_refs


def _show_embed(url: str, content_type: str):
    if content_type.startswith("image/"):
        response = requests.get(url)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        image.show()
