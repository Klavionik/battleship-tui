from typing import Any

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Mount
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
        self.loading = True  # noqa
        self.login(guest=True)

    @on(Button.Pressed, "#connect-user")
    async def connect_as_user(self) -> None:
        self.loading = True  # noqa
        self.login()

    @work
    async def login(self, guest: bool = False) -> None:
        client = get_client()

        if guest:
            nickname = await client.login_as_guest()
        else:
            nickname = await client.login(self._nickname, self._password)

        await client.connect()
        await self.app.switch_screen(screens.Lobby(nickname=nickname))
