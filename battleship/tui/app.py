import asyncio
import sys
from typing import Any, cast

import inject
from loguru import logger
from sentry_sdk import capture_exception
from textual import on, work
from textual.app import App
from textual.events import Mount, Unmount
from textual.screen import Screen

from battleship.client import Client, ClientError, ConnectionEvent
from battleship.tui import screens, strategies
from battleship.tui.widgets import modals
from battleship.tui.widgets.modals import WaitingModal


class BattleshipError(Exception):
    pass


class BattleshipApp(App[None]):
    BINDINGS = [("ctrl+q", "quit", "Quit")]
    TITLE = "Battleship"
    SUB_TITLE = "The Game"
    CSS_PATH = "styles.tcss"
    ENABLE_COMMAND_PALETTE = False

    @inject.param("client", Client)
    def __init__(
        self,
        *args: Any,
        mount_screen: Screen[Any] | None = None,
        client: Client,
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._mount_screen = mount_screen or screens.MainMenu()
        self._client = client
        self._debug = debug
        self.error_text = ""

        self._client.add_listener(ConnectionEvent.CONNECTION_LOST, self._handle_connection_lost)

    @classmethod
    def singleplayer(cls, roster: str, firing_order: str, salvo_mode: bool) -> "BattleshipApp":
        singleplayer_screen = screens.Singleplayer()

        def start_game() -> None:
            singleplayer_screen.start_game(roster, firing_order, salvo_mode)

        instance: BattleshipApp = cls(mount_screen=singleplayer_screen)
        instance.call_later(start_game)
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
            await waiting_modal.dismiss(False)
        else:
            await waiting_modal.dismiss(True)

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

        logger.debug(
            "Handle connection loss: show the modal, "
            "setup handlers in case it is restored (or lost forever)."
        )
        modal = modals.ConnectionLostModal()

        # Not a very clean way of dismissing this waiting modal, probably.
        # If we don't do this, we end up with 1) double overlay 2) player
        # thinking that his session is still about to start (if connection restore).
        if hasattr(self, "_create_game_waiting_modal"):
            self._create_game_waiting_modal.dismiss(False)

        await self.push_screen(modal)

        def handle_connection_established() -> None:
            logger.debug("Connection restored.")
            self._client.remove_listener(
                ConnectionEvent.CONNECTION_IMPOSSIBLE, handle_connection_impossible
            )
            modal.dismiss()
            cancel_active_game()

        def handle_connection_impossible() -> None:
            logger.debug("Unable to restore connection, return to the main menu.")
            self._client.remove_listener(
                ConnectionEvent.CONNECTION_ESTABLISHED, handle_connection_established
            )
            modal.dismiss()
            cancel_active_game()

            # Keep only the default screen, just in case.
            for _ in self.screen_stack[1:]:
                self.pop_screen()

            # Now return to the main menu.
            self.push_screen(screens.MainMenu())
            self.notify(
                "Unable to re-establish connection.",
                title="Connection lost",
                severity="warning",
                timeout=5,
            )

        self._client.add_listener(
            ConnectionEvent.CONNECTION_IMPOSSIBLE, handle_connection_impossible, once=True
        )
        self._client.add_listener(
            ConnectionEvent.CONNECTION_ESTABLISHED, handle_connection_established, once=True
        )

    def _fatal_error(self) -> None:
        _, exc_value, _ = sys.exc_info()

        if not self._debug:
            event_id = capture_exception()
            error_text = "Oops, an unexpected error occured in Battleship TUI: %s. Event ID: %s."
            self.error_text = error_text % (str(exc_value), event_id)
            self._close_messages_no_wait()
        else:
            super()._fatal_error()


def run(app: BattleshipApp | None = None, debug: bool = False) -> None:
    if app is None:
        app = BattleshipApp(debug=debug)

    app.run()

    if app.return_code != 0:
        raise BattleshipError(app.error_text)
