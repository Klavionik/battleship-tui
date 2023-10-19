from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Markdown

from battleship.engine import session
from battleship.tui import resources, screens
from battleship.tui.widgets.new_game import NewGame


class Singleplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with resources.get_resource("singleplayer_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield NewGame()

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(NewGame.PlayPressed)
    def start_game(self, event: NewGame.PlayPressed) -> None:
        def session_factory() -> session.SingleplayerSession:
            return session.SingleplayerSession(
                "Player", event.roster, event.firing_order, event.salvo_mode
            )

        self.app.switch_screen(screens.Game(session_factory=session_factory))
