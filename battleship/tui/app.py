from typing import Any

import inject
from loguru import logger
from textual import on
from textual.app import App
from textual.events import Mount, Unmount
from textual.screen import Screen

from battleship.client import Client
from battleship.engine import domain
from battleship.shared.events import ClientEvent
from battleship.tui import screens, strategies
from battleship.tui.widgets import modals


class BattleshipApp(App[None]):
    BINDINGS = [("q", "quit", "Quit"), ("F1", "show_help", "Help")]
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
        game_screen = screens.Game(game=game, strategy=strategy)
        instance: BattleshipApp = cls(mount_screen=game_screen)
        return instance

    @on(Mount)
    def mount_first_screen(self) -> None:
        self.push_screen(self._mount_screen)

    @on(Unmount)
    async def disconnect(self) -> None:
        await self._client.disconnect()

    def _handle_connection_lost(self) -> None:
        logger.warning("Connection lost, trying to re-establish.")
        modal = modals.ConnectionLostModal()

        def restore_listeners() -> None:
            self._client.remove_listener(ClientEvent.CONNECTION_ESTABLISHED, on_connection_restored)
            self._client.remove_listener(
                ClientEvent.CONNECTION_IMPOSSIBLE,
                on_connection_impossible,
            )

        def on_connection_restored() -> None:
            logger.debug("Connection restored.")
            modal.dismiss()
            restore_listeners()

        async def on_connection_impossible() -> None:
            modal.dismiss()
            restore_listeners()

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

        self._client.add_listener(ClientEvent.CONNECTION_ESTABLISHED, on_connection_restored)
        self._client.add_listener(ClientEvent.CONNECTION_IMPOSSIBLE, on_connection_impossible)

        self.push_screen(modal)


def run(app: BattleshipApp | None = None) -> None:
    if app is None:
        app = BattleshipApp()

    app.run()
