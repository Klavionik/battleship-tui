import asyncio
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

from battleship.client import Client
from battleship.server import GameEvent


class Menu(Static):
    def compose(self) -> ComposeResult:
        container = Container(
            Static(f"Logged in as [b]{self.app.nickname}[/b]"),  # type: ignore
            Button(label="New game", id="new_game"),
            Button(label="Join", id="join"),
            Button(label="Logout", id="logout"),
            classes="panel center",
        )
        container.border_title = "Menu"
        yield container


class MenuScreen(Screen[None]):
    class Logout(Message):
        pass

    def compose(self) -> ComposeResult:
        yield Menu()

    @on(Button.Pressed, "#logout")
    async def emit_logout(self) -> None:
        self.post_message(self.Logout())


class Login(Static):
    WELCOME_TEXT = "Welcome to Battleship! Enter your nickname and press Enter to connect."
    BINDINGS = [("Enter", "connect", "Connect")]

    class Connect(Message):
        def __init__(self, nickname: str):
            self.nickname = nickname
            super().__init__()

    def compose(self) -> ComposeResult:
        container = Container(Static(self.WELCOME_TEXT), Input(), classes="panel")
        container.border_title = "Login"
        yield container

    @on(Input.Submitted)
    def emit_connect(self, event: Input.Submitted) -> None:
        self.post_message(self.Connect(event.value))


class BattleshipApp(App[None]):
    CSS_PATH = "styles.css"
    SCREENS = {"menu": MenuScreen()}
    BINDINGS = [("ctrl+q", "quit", "Quit")]
    TITLE = "Battleship"
    SUB_TITLE = "Multiplayer Game"

    def __init__(self, *args: Any, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        @client.on(GameEvent.CONNECTED)
        async def on_connected(_: Any) -> None:
            await self.push_screen("menu")

        @client.on("error")
        async def on_error(error: Any) -> None:
            self.log(error)

        self.client = client

    def compose(self) -> ComposeResult:
        yield Header()
        yield Login()
        yield Footer()

    @on(Login.Connect)
    async def connect(self, event: Login.Connect) -> None:
        self.log("Connecting...")
        await self.client.connect(event.nickname)
        self.nickname = event.nickname

    @on(MenuScreen.Logout)
    async def disconnect(self) -> None:
        await self.client.disconnect()
        self.pop_screen()


async def _run() -> None:
    async with Client("localhost", 8000) as client:
        app = BattleshipApp(client=client)
        await app.run_async()


def run() -> None:
    asyncio.run(_run())
