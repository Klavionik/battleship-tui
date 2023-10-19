from typing import Any

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Markdown

from battleship.tui import resources
from battleship.tui.widgets.new_game import NewGame


class CreateGame(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with resources.get_resource("create_game_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with Container(classes="screen-help"):
                yield Markdown(self.help)

            with Container(classes="screen-content"):
                yield NewGame(with_name=True)

        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()
