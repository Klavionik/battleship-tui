import asyncio
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Markdown, Rule

from battleship.client import get_client
from battleship.tui import resources, screens


class Multiplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with resources.get_resource("multiplayer_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield Input(placeholder="Nickname")
                yield Input(placeholder="Password")
                yield Button("Connect", variant="primary", id="connect-user")
                yield Rule(line_style="heavy")
                yield Button("Connect as guest", id="connect-guest")

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Button.Pressed, "#connect-guest")
    async def connect_as_guest(self) -> None:
        self.loading = True  # noqa
        client = get_client()
        await client.connect()

        async def switch_to_lobby() -> None:
            nickname = await client.login()
            await self.app.switch_screen(screens.Lobby(nickname=nickname))

        asyncio.create_task(switch_to_lobby())
