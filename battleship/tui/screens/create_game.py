from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Label, LoadingIndicator, Markdown

from battleship.client.realtime import get_client
from battleship.tui import resources
from battleship.tui.widgets.new_game import NewGame


class WaitingModal(ModalScreen[None]):
    def __init__(self, *args: Any, session_id: str, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._session_id = session_id

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Waiting for the second player...")
            yield LoadingIndicator()
            yield Button("Abort", variant="error")

    @on(Button.Pressed)
    async def abort_waiting(self) -> None:
        client = get_client()
        await client.abort_game(self._session_id)
        self.app.pop_screen()


class CreateGame(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with resources.get_resource("create_game_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with Container(classes="screen-help"):
                yield Markdown(self.help)

            with Container(classes="screen-content"):
                yield NewGame(with_name=True)

        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()

    @on(NewGame.PlayPressed)
    async def announce_game(self, event: NewGame.PlayPressed) -> None:
        client = get_client()
        name = event.name or f"{client.nickname}'s game"
        session = await client.create_session(
            name,
            event.roster.name,
            event.firing_order,
            event.salvo_mode,
        )
        await self.app.push_screen(WaitingModal(session_id=session.id))
