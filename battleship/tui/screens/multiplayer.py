from typing import Any

import inject
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Mount
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Markdown, Rule

from battleship.client import Client, RequestFailed
from battleship.tui import resources, screens


class Multiplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    @inject.param("client", Client)
    def __init__(self, *args: Any, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = client

        with resources.get_resource("multiplayer_help.md").open() as fh:
            self.help = fh.read()

        self._nickname = ""
        self._password = ""

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield Input(placeholder="Nickname", id="nickname")
                yield Input(placeholder="Password", id="password", password=True)
                yield Button("Connect", variant="primary", id="connect-user")
                yield Rule(line_style="heavy")
                yield Button("Connect as guest", id="connect-guest")

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Mount)
    def on_mount(self) -> None:
        self.query_one("#nickname", Input).focus()

    @on(Input.Changed, "#nickname")
    def update_nickname(self, event: Input.Changed) -> None:
        self._nickname = event.value

    @on(Input.Changed, "#password")
    def update_password(self, event: Input.Changed) -> None:
        self._password = event.value

    @on(Button.Pressed, "#connect-guest")
    async def connect_as_guest(self) -> None:
        self.login(guest=True)

    @on(Button.Pressed, "#connect-user")
    async def connect_as_user(self) -> None:
        self.login()

    @work
    async def login(self, guest: bool = False) -> None:
        self.loading = True  # noqa

        try:
            if guest:
                nickname = await self._client.login(guest=True)
            else:
                nickname = await self._client.login(self._nickname, self._password)
        except RequestFailed:
            self.loading = False  # noqa
            self.notify(
                "Cannot send the request, check your internet connection and try later.",
                title="Request failed",
                severity="error",
                timeout=5,
            )
        else:
            await self.app.switch_screen(screens.Lobby(nickname=nickname))
