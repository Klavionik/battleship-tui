from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Markdown, Static

from battleship.client.realtime import get_client
from battleship.tui import resources, screens


class Lobby(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, nickname: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._nickname = nickname

        with resources.get_resource("lobby_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with Container(classes="screen-help"):
                yield Markdown(self.help)

            with Container(classes="screen-content"):
                yield Static(f"👤{self._nickname}", id="username")

                with ListView():
                    yield ListItem(Label("🎯 Create game"), id="create_game")
                    yield ListItem(Label("🔍 Join game"))
                    yield ListItem(Label("📜 Statistics"))
                    yield ListItem(Label("👋 Logout"), id="logout")

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(ListView.Selected, item="#logout")
    async def logout(self) -> None:
        client = get_client()
        await client.logout()
        await self.app.switch_screen(screens.Multiplayer())

    @on(ListView.Selected, item="#create_game")
    async def create_game(self) -> None:
        await self.app.push_screen(screens.CreateGame())
