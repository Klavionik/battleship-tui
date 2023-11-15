from typing import Any

import inject
from loguru import logger
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Markdown

from battleship.client import Client
from battleship.engine.roster import Roster, RosterItem
from battleship.shared.events import ServerEvent
from battleship.tui import resources, screens, strategies
from battleship.tui.widgets.modals import WaitingModal
from battleship.tui.widgets.new_game import NewGame


class CreateGame(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    @inject.param("client", Client)
    def __init__(self, *args: Any, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = client

        with resources.get_resource("create_game_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield NewGame(with_name=True)

        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()

    @on(NewGame.PlayPressed)
    async def create_session(self, event: NewGame.PlayPressed) -> None:
        nickname = self._client.nickname
        name = event.name or f"{nickname}'s game"
        session = await self._client.create_session(
            name,
            event.roster,
            event.firing_order,
            event.salvo_mode,
        )
        waiting_modal = WaitingModal()
        self.app._create_game_waiting_modal = waiting_modal  # type: ignore[attr-defined]

        @logger.catch
        def on_start_game(payload: dict[str, Any]) -> None:
            enemy_nickname = payload["enemy"]
            data = payload["roster"]
            roster = Roster(name=data["name"], items=[RosterItem(*item) for item in data["items"]])
            strategy = strategies.MultiplayerStrategy(
                self._client.nickname,
                enemy_nickname,
                roster,
                event.firing_order,
                event.salvo_mode,
                self._client,
            )
            waiting_modal.dismiss(True)
            self.app.push_screen(screens.Game(strategy=strategy))

        self._client.add_listener(ServerEvent.START_GAME, on_start_game)

        async def on_modal_dismiss(game_started: bool) -> None:
            del self.app._create_game_waiting_modal  # type: ignore[attr-defined]
            self._client.remove_listener(ServerEvent.START_GAME, on_start_game)

            if not game_started:
                try:
                    await self._client.delete_session(session.id)
                except Exception as exc:
                    logger.warning(f"Could not delete created session {session.id}. Error: {exc}")

        await self.app.push_screen(waiting_modal, callback=on_modal_dismiss)
