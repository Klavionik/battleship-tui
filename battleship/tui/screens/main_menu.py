from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Markdown

from battleship.tui import screens

WELCOME_TEXT = """
# Welcome to Battleship TUI!

Battleship TUI is an implementation of the classic Battleship game
for your terminal.

You can play against the AI or against a real player
via network.
"""


class MainMenu(Screen[None]):
    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            yield Markdown(WELCOME_TEXT, classes="screen-help")

            with ListView(id="menu"):
                yield ListItem(Label(":robot: Singleplayer"), id="singleplayer")
                yield ListItem(Label(":man: Multiplayer"), id="multiplayer")
                yield ListItem(Label(":wrench: Settings"), id="settings")

        yield Footer()

    @on(ListView.Selected)
    def select_screen(self, event: ListView.Selected) -> None:
        match event.item.id:
            case "singleplayer":
                self.app.switch_screen(screens.Singleplayer())
            case "multiplayer":
                self.app.switch_screen(screens.Multiplayer())
