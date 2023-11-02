from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Label, LoadingIndicator, Markdown

from battleship.client import get_client
from battleship.engine import create_game
from battleship.engine.roster import Roster, RosterItem
from battleship.logger import client_logger as logger
from battleship.shared.events import ServerEvent
from battleship.tui import resources, screens, strategies
from battleship.tui.widgets.new_game import NewGame


class WaitingModal(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Waiting for the second player...")
            yield LoadingIndicator()
            yield Button("Abort", variant="error")

    @on(Button.Pressed)
    async def abort_waiting(self) -> None:
        self.dismiss(None)


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
    async def create_session(self, event: NewGame.PlayPressed) -> None:
        client = get_client()
        assert client.user
        nickname = client.user.nickname
        name = event.name or f"{nickname}'s game"
        session = await client.create_session(
            name,
            event.roster,
            event.firing_order,
            event.salvo_mode,
        )
        waiting_modal = WaitingModal()

        @logger.catch
        def on_start_game(payload: dict[str, Any]) -> None:
            enemy_nickname = payload["enemy"]
            data = payload["roster"]
            roster = Roster(name=data["name"], items=[RosterItem(*item) for item in data["items"]])
            game = create_game(
                nickname, enemy_nickname, roster, event.firing_order, event.salvo_mode
            )
            strategy = strategies.MultiplayerStrategy(client)
            waiting_modal.dismiss(None)
            self.app.switch_screen(screens.Game(game=game, strategy=strategy))

        client.add_listener(ServerEvent.START_GAME, on_start_game)

        async def on_modal_dismiss(result: None) -> None:
            client.remove_listener(ServerEvent.START_GAME, on_start_game)
            await client.delete_session(session.id)

        await self.app.push_screen(waiting_modal, callback=on_modal_dismiss)
