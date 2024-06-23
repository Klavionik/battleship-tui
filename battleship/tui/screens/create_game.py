from typing import Any

import inject
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Markdown

from battleship.client import Client
from battleship.tui import resources
from battleship.tui.widgets import AppFooter
from battleship.tui.widgets.new_game import NewGame


class CreateGame(Screen[None]):
    class CreateMultiplayerSession(Message):
        def __init__(self, game_name: str, roster_name: str, firing_order: str, salvo_mode: bool):
            super().__init__()
            self.game_name = game_name
            self.roster_name = roster_name
            self.firing_order = firing_order
            self.salvo_mode = salvo_mode

    BINDINGS = [("escape", "back", "Back")]

    @inject.param("client", Client)
    def __init__(self, *args: Any, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = client

        with resources.get_resource("create_game_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="container"):
            with VerticalScroll():
                yield Markdown(
                    self.help,
                )

            with Container():
                yield NewGame(with_name=True)

        yield AppFooter()

    def action_back(self) -> None:
        self.app.pop_screen()

    @on(NewGame.PlayPressed)
    def create_session_from_event(self, event: NewGame.PlayPressed) -> None:
        self.post_message(
            self.CreateMultiplayerSession(
                event.name,
                event.roster,
                event.firing_order,
                event.salvo_mode,
            )
        )
