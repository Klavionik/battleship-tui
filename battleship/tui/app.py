import asyncio
from typing import Any, cast

import inject
from loguru import logger
from textual import on, work
from textual.app import App
from textual.events import Mount, Unmount
from textual.screen import Screen

from battleship.client import Client, ClientError, ConnectionImpossible
from battleship.engine import domain
from battleship.shared.events import ClientEvent
from battleship.tui import screens, strategies
from battleship.tui.widgets import modals
from battleship.tui.widgets.modals import WaitingModal


class BattleshipApp(App[None]):
    BINDINGS = [("ctrl+q", "quit", "Quit")]
    TITLE = "Battleship"
    SUB_TITLE = "The Game"
    CSS_PATH = "styles.tcss"

    @inject.param("client", Client)
    def __init__(
        self, *args: Any, mount_screen: Screen[Any] | None = None, client: Client, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._mount_screen = mount_screen or screens.MainMenu()
        self._client = client

        self._client.add_listener(ClientEvent.CONNECTION_LOST, self._handle_connection_lost)

    @classmethod
    def singleplayer(cls, game: domain.Game) -> "BattleshipApp":
        strategy = strategies.SingleplayerStrategy(game)
        game_screen = screens.Game(strategy=strategy)
        instance: BattleshipApp = cls(mount_screen=game_screen)
        return instance

    @classmethod
    def multiplayer_new(
        cls, game_name: str, roster_name: str, firing_order: str, salvo_mode: bool
    ) -> "BattleshipApp":
        multiplayer_screen = screens.Multiplayer()

        def create_session() -> None:
            instance.create_multiplayer_session(game_name, roster_name, firing_order, salvo_mode)

        instance: BattleshipApp = cls(mount_screen=multiplayer_screen)
        instance.call_later(create_session)
        return instance

    @classmethod
    def multiplayer_join(cls, game_code: str) -> "BattleshipApp":
        multiplayer_screen = screens.Multiplayer()

        def join_session() -> None:
            instance.join_multiplayer_session(game_code)

        instance: BattleshipApp = cls(mount_screen=multiplayer_screen)
        instance.call_later(join_session)
        return instance

    @on(Mount)
    def mount_first_screen(self) -> None:
        self.push_screen(self._mount_screen)

    @on(Unmount)
    async def disconnect(self) -> None:
        await self._client.disconnect()

    @on(screens.CreateGame.CreateMultiplayerSession)
    def create_session_from_event(self, event: screens.CreateGame.CreateMultiplayerSession) -> None:
        self.create_multiplayer_session(
            event.game_name,
            event.roster_name,
            event.firing_order,
            event.salvo_mode,
        )

    @work
    async def create_multiplayer_session(
        self, name: str, roster_name: str, firing_order: str, salvo_mode: bool
    ) -> None:
        if not self._client.logged_in:
            logger.warning("Cannot create multiplayer session if not logged in.")
            return

        name = name or f"{self._client.nickname}'s game"

        session = await self._client.create_session(
            name,
            roster_name,
            firing_order,
            salvo_mode,
        )

        strategy = strategies.MultiplayerStrategy(self._client.nickname, self._client)

        waiting_modal = WaitingModal(game_code=session.id)
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

    @on(screens.JoinGame.JoinMultiplayerSession)
    async def join_from_event(self, event: screens.JoinGame.JoinMultiplayerSession) -> None:
        self.join_multiplayer_session(event.session_id)

    @work
    async def join_multiplayer_session(self, session_id: str) -> None:
        strategy = strategies.MultiplayerStrategy(self._client.nickname, self._client)

        await self._client.join_game(session_id)

        try:
            await strategy.started()
        except strategies.GameNeverStarted:
            self.notify(
                "Waiting too long to join the game.",
                title="Game start aborted",
                severity="warning",
                timeout=5,
            )
        else:
            await self.app.push_screen(screens.Game(strategy=strategy))

    async def _handle_connection_lost(self) -> None:
        def cancel_active_game() -> None:
            if isinstance(self.screen, screens.Game):
                game_screen = cast(screens.Game, self.pop_screen())
                game_screen.cancel_game()
                self.notify(
                    "Game cannot be continued.",
                    title="Connection lost",
                    severity="error",
                    timeout=5,
                )

        logger.warning("Connection lost, trying to re-establish.")
        modal = modals.ConnectionLostModal()

        # Not a very clean way of dismissing this waiting modal, probably.
        # If we don't do this, we end up with 1) double overlay 2) player
        # thinking that his session is still about to start (if connection restore).
        if hasattr(self, "_create_game_waiting_modal"):
            self._create_game_waiting_modal.dismiss(False)

        await self.push_screen(modal)

        try:
            await self._client.await_connection()
            logger.debug("Connection restored.")
            modal.dismiss()
            cancel_active_game()
        except ConnectionImpossible:
            modal.dismiss()
            cancel_active_game()

            logger.warning("Unable to restore connection, return to the main menu.")

            # Keep only the default screen, just in case.
            for _ in self.screen_stack[1:]:
                self.pop_screen()

            # Now return to the main menu.
            await self.push_screen(screens.MainMenu())
            self.notify(
                "Unable to re-establish connection.",
                title="Connection lost",
                severity="warning",
                timeout=5,
            )


def run(app: BattleshipApp | None = None) -> None:
    if app is None:
        app = BattleshipApp()

    app.run()
