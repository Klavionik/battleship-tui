from typing import Any

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Input, Label, ListItem, ListView, Markdown

from battleship.tui import resources, screens


class Multiplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with resources.get_resource("multiplayer_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            yield Markdown(self.help, id="text")

            with Container(id="menu"):
                yield Input(placeholder="Nickname")

                with ListView():
                    yield ListItem(Label("New game"))
                    yield ListItem(Label("Join game"))

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())
