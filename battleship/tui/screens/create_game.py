import asyncio
from typing import Any

import inject
from loguru import logger
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Markdown

from battleship.client import Client, ClientError
from battleship.tui import resources, screens, strategies
from battleship.tui.widgets import AppFooter
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

        yield AppFooter()

    def action_back(self) -> None:
        self.app.pop_screen()

    @on(NewGame.PlayPressed)
    def create_session_from_event(self, event: NewGame.PlayPressed) -> None:
        nickname = self._client.nickname
        name = event.name or f"{nickname}'s game"
        self.create_session(
            name,
            event.roster,
            event.firing_order,
            event.salvo_mode,
        )

    @work
    async def create_session(
        self, name: str, roster_name: str, firing_order: str, salvo_mode: bool
    ) -> None:
        session = await self._client.create_session(
            name,
            roster_name,
            firing_order,
            salvo_mode,
        )

        strategy = strategies.MultiplayerStrategy(
            self._client.nickname,
            firing_order,
            salvo_mode,
            self._client,
        )

        waiting_modal = WaitingModal()
        self.app._create_game_waiting_modal = waiting_modal  # type: ignore[attr-defined]

        async def on_modal_dismiss(game_started: bool) -> None:
            del self.app._create_game_waiting_modal  # type: ignore[attr-defined]

            if game_started:
                await self.app.push_screen(screens.Game(strategy=strategy))
                return

            game_started_task.cancel()

            try:
                await self._client.delete_session(session.id)
            except ClientError as exc:
                logger.warning(f"Could not delete created session {session.id}. Error: {exc}")

        await self.app.push_screen(waiting_modal, callback=on_modal_dismiss)

        try:
            game_started_task = asyncio.create_task(strategy.started())
            await game_started_task
        except strategies.GameNeverStarted:
            self.notify(
                "Waiting too long for the second player.",
                title="Game start aborted",
                severity="warning",
                timeout=5,
            )
            waiting_modal.dismiss(False)
        else:
            waiting_modal.dismiss(True)
