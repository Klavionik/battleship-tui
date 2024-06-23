from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Markdown

from battleship.tui import screens
from battleship.tui.widgets import AppFooter

WELCOME_TEXT = """
# Welcome to Battleship TUI!

Battleship TUI is an implementation of the classic Battleship game
for your terminal.

You can play against the computer or against a real player
via network.
"""


class MainMenu(Screen[None]):
    def compose(self) -> ComposeResult:
        with Container(classes="container middle"):
            yield Markdown(WELCOME_TEXT)

            with ListView():
                yield ListItem(Label(":robot: Singleplayer"), id="singleplayer")
                yield ListItem(Label(":man: Multiplayer"), id="multiplayer")
                yield ListItem(Label(":wrench: Settings"), id="settings")

        yield AppFooter()

    @on(ListView.Selected, item="#singleplayer")
    def run_singleplayer(self) -> None:
        self.app.switch_screen(screens.Singleplayer())

    @on(ListView.Selected, item="#multiplayer")
    def run_multiplayer(self) -> None:
        self.app.switch_screen(screens.Multiplayer())

    @on(ListView.Selected, item="#settings")
    def to_settings(self) -> None:
        self.app.switch_screen(screens.Settings())
