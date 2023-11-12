from typing import Any

import inject
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Mount
from textual.reactive import var
from textual.screen import Screen
from textual.validation import Length
from textual.widgets import Button, Footer, Input, Markdown, Rule

from battleship.client import Client, RequestFailed, Unauthorized
from battleship.tui import resources, screens


class Multiplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]
    is_nickname_valid: var[bool] = var(False)
    is_password_valid: var[bool] = var(False)
    is_input_valid: var[bool] = var(False)

    @inject.param("client", Client)
    def __init__(self, *args: Any, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = client

        with resources.get_resource("multiplayer_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield Input(
                    placeholder="Nickname",
                    id="nickname",
                    validators=[Length(minimum=7, maximum=20)],
                )
                yield Input(
                    placeholder="Password",
                    id="password",
                    password=True,
                    validators=[Length(minimum=9)],
                )
                yield Button("Connect", variant="primary", id="connect-user", disabled=True)
                yield Rule(line_style="heavy")
                yield Button("Connect as guest", id="connect-guest")

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Mount)
    def on_mount(self) -> None:
        self.query_one("#nickname", Input).focus()

    def compute_is_input_valid(self) -> bool:
        return self.is_password_valid and self.is_nickname_valid

    def watch_is_input_valid(self, old_valid: bool, valid: bool) -> None:
        if old_valid == valid:
            return

        self.query_one("#connect-user", Button).disabled = not valid

    @on(Input.Changed)
    def validate_nickname(self, event: Input.Changed) -> None:
        validation = event.validation_result

        if validation is not None:
            if event.input.id == "nickname":
                self.is_nickname_valid = validation.is_valid  # noqa

            if event.input.id == "password":
                self.is_password_valid = validation.is_valid  # noqa

    @on(Input.Submitted)
    def submit(self) -> None:
        if self.is_input_valid:
            self.login()

    @on(Button.Pressed, "#connect-guest")
    def connect_as_guest(self) -> None:
        self.login(guest=True)

    @on(Button.Pressed, "#connect-user")
    def connect_as_user(self) -> None:
        self.login()

    @work
    async def login(self, guest: bool = False) -> None:
        self.loading = True  # noqa

        try:
            if guest:
                nickname = await self._client.login(guest=True)
            else:
                nickname = self.query_one("#nickname", Input).value
                password = self.query_one("#password", Input).value
                await self._client.login(nickname, password)
        except RequestFailed:
            self.notify(
                "Cannot send the request, check your internet connection and try later.",
                title="Request failed",
                severity="error",
                timeout=5,
            )
        except Unauthorized:
            self.notify(
                "Incorrect nickname or password.",
                title="Unauthorized",
                severity="error",
                timeout=5,
            )
        else:
            await self.app.switch_screen(screens.Lobby(nickname=nickname))
        finally:
            self.loading = False  # noqa
