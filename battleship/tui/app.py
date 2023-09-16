import asyncio
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from battleship.client import RealtimeClient
from battleship.shared.events import EventPayload, ServerEvent


class MenuScreen(Screen[None]):
    nickname = reactive("")

    class Logout(Message):
        pass

    def compose(self) -> ComposeResult:
        container = Container(
            Static(f"Logged in as [b]{self.nickname}[/b]"),
            Button(label="New game", id="new_game"),
            Button(label="Join", id="join"),
            Button(label="Logout", id="logout"),
            classes="panel center",
        )
        container.border_title = "Menu"
        yield container

    @on(Button.Pressed, "#logout")
    async def emit_logout(self) -> None:
        self.post_message(self.Logout())


class LoginScreen(Screen[None]):
    WELCOME_TEXT = "Welcome to Battleship! Enter your nickname and press Enter to connect."
    BINDINGS = [("Enter", "connect", "Connect")]

    class Login(Message):
        def __init__(self, nickname: str):
            self.nickname = nickname
            super().__init__()

    def compose(self) -> ComposeResult:
        container = Container(Static(self.WELCOME_TEXT), Input(), classes="panel")
        container.border_title = "Login"
        yield container

    @on(Input.Submitted)
    def emit_connect(self, event: Input.Submitted) -> None:
        self.post_message(self.Login(event.value))


class BattleshipApp(App[None]):
    CSS_PATH = "styles.css"
    BINDINGS = [("ctrl+q", "quit", "Quit")]
    TITLE = "Battleship"
    SUB_TITLE = "Multiplayer Game"

    def __init__(self, *args: Any, client: RealtimeClient, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        @client.on(ServerEvent.LOGIN)
        async def on_connected(payload: EventPayload) -> None:
            menu = MenuScreen()
            menu.nickname = payload["nickname"]
            await self.switch_screen(menu)

        @client.on("error")
        async def on_error(error: Any) -> None:
            self.log(error)

        self.client = client

    async def on_mount(self) -> None:
        await self.client.connect()
        await self.push_screen(LoginScreen())

    async def on_unmount(self) -> None:
        await self.client.disconnect()

    @on(LoginScreen.Login)
    async def login(self, event: LoginScreen.Login) -> None:
        self.log("Connecting...")
        await self.client.login(event.nickname)

    @on(MenuScreen.Logout)
    async def disconnect(self) -> None:
        await self.client.logout()
        await self.switch_screen(LoginScreen())


async def _run() -> None:
    client = RealtimeClient("localhost", 8000)
    app = BattleshipApp(client=client)

    try:
        await app.run_async()
    finally:
        await client.disconnect()


def run() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    run()
