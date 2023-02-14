#!/usr/bin/env python3

import click
import prompt_toolkit
import requests
import rich.console as rich_console

from fixieai.client import FixieClient

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
                            f"   [dim]@{message['sentBy']}: {message['text']}[/]"
                        )
                    else:
                        textconsole.print(f"{self._response_index}❯ {message['text']}")
            except requests.exceptions.HTTPError as e:
                textconsole.print(f"🚨 {e}")
                return


@click.group()
@click.option(
    "--fixie_api_url",
    help="Fixie API URL. Defaults to the value of the FIXIE_API_URL env var, "
    "or `https://app.fixie.ai` if that is unset.",
)
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def fixie(ctx, fixie_api_url, verbose):
    ctx.ensure_object(dict)
    client = FixieClient(api_url=fixie_api_url)
    ctx.obj["fixie_API_URL"] = fixie_api_url
    ctx.obj["CLIENT"] = client
    ctx.obj["VERBOSE"] = verbose


@fixie.command("console", help="Run live console.")
@click.pass_context
def console(ctx):
    client = ctx.obj["CLIENT"]
    c = Console(client)
    c.run()


@fixie.group(help="Agent-related commands.")
def agents():
    pass


@agents.command("list", help="List agents.")
@click.pass_context
def list_agents(ctx):
    client = ctx.obj["CLIENT"]
    agents = client.get_agents()
    for agent_id, agent in agents.items():
        textconsole.print(f"[green]{agent_id}[/]: {agent['name']}")
        if ctx.obj["VERBOSE"]:
            textconsole.print(f"    {agent['description']}")
            textconsole.print(f"    [yellow]Developer[/]: {agent['developer']}")
            if "moreInfo" in agent and agent["moreInfo"]:
                textconsole.print(f"    [yellow]More info[/]: {agent['moreInfo']}")
            textconsole.print("")


@fixie.group(help="Session-related commands.")
def sessions():
    pass


@sessions.command("list", help="List sessions.")
@click.pass_context
def list_sessions(ctx):
    client = ctx.obj["CLIENT"]
    session_ids = client.get_sessions()
    for session_id in session_ids:
        textconsole.print(f"[green]{session_id}[/]")


@sessions.command("show", help="Show session.")
@click.pass_context
@click.argument("session_id")
def show_session(ctx, session_id: str):
    client = ctx.obj["CLIENT"]
    session = client.get_session(session_id)
    messages = session.get_messages()
    textconsole.print(messages)


@sessions.command("embeds", help="Show embeds in a session.")
@click.pass_context
@click.argument("session_id")
def embeds(ctx, session_id: str):
    client = ctx.obj["CLIENT"]
    session = client.get_session(session_id)
    embeds = session.get_embeds()
    textconsole.print(embeds)


if __name__ == "__main__":
    fixie()
