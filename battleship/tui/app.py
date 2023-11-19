from typing import Any, cast

import inject
from loguru import logger
from textual import on
from textual.app import App
from textual.events import Mount, Unmount
from textual.screen import Screen

from battleship.client import Client, ConnectionImpossible
from battleship.engine import domain
from battleship.shared.events import ClientEvent
from battleship.tui import screens, strategies
from battleship.tui.widgets import modals


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

    @on(Mount)
    def mount_first_screen(self) -> None:
        self.push_screen(self._mount_screen)

    @on(Unmount)
    async def disconnect(self) -> None:
        await self._client.disconnect()

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
