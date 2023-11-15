from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Markdown

from battleship.engine import create_game
from battleship.engine.roster import get_roster
from battleship.tui import resources, screens, strategies
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
        roster = get_roster(event.roster)
        game = create_game(
            "Player",
            "Computer",
            roster=roster,
            firing_order=event.firing_order,
            salvo_mode=event.salvo_mode,
        )
        self.app.push_screen(screens.Game(strategy=strategies.SingleplayerStrategy(game)))
