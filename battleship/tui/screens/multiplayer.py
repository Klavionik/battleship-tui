from typing import Any

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Markdown, Rule

from battleship.tui import resources, screens


class Multiplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with resources.get_resource("multiplayer_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield Input(placeholder="Nickname")
                yield Input(placeholder="Password")
                yield Button("Connect", variant="primary")
                yield Rule(line_style="heavy")
                yield Button("Connect as guest")

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())
