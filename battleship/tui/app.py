from typing import Any

import inject
from textual import on
from textual.app import App
from textual.events import Mount, Unmount
from textual.screen import Screen

from battleship.client import Client
from battleship.engine import domain
from battleship.tui import screens, strategies


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


def run(app: BattleshipApp | None = None) -> None:
    if app is None:
        app = BattleshipApp()

    app.run()
