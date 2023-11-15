from typing import Any

import inject
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Mount, Unmount
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Markdown, Static

from battleship.client import Client, ClientError
from battleship.tui import resources, screens


class Lobby(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    @inject.param("client", Client)
    def __init__(self, *args: Any, nickname: str, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._nickname = nickname
        self._client = client

        with resources.get_resource("lobby_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield Static(f"👤{self._nickname}", id="username")

                with ListView():
                    yield ListItem(Label("🎯 Create game"), id="create_game")
                    yield ListItem(Label("🔍 Join game"), id="join_game")
                    yield ListItem(Label("📜 Statistics"), id="stats")
                    yield ListItem(Label("👋 Logout"), id="logout")

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Mount)
    def focus_menu(self) -> None:
        self.query_one(ListView).focus()

    @on(Unmount)
    async def disconnect_ws(self) -> None:
        await self._client.disconnect()

    @on(ListView.Selected, item="#logout")
    async def logout(self) -> None:
        await self._client.disconnect()
        await self._client.logout()
        self.action_back()

    @on(ListView.Selected, item="#create_game")
    def create_game(self) -> None:
        self.app.push_screen(screens.CreateGame())

    @on(ListView.Selected, item="#join_game")
    async def join_game(self) -> None:
        await self.app.push_screen(screens.JoinGame())

    @on(ListView.Selected, item="#stats")
    async def show_statistics(self) -> None:
        self.loading = True  # noqa

        try:
            statistics = await self._client.fetch_statistics()
            await self.app.push_screen(screens.Statistics(data=statistics))
        except ClientError:
            self.notify(
                "Cannot load statistics", title="Loading error", severity="error", timeout=5
            )
        finally:
            self.loading = False  # noqa
