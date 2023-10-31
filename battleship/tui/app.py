from typing import Any, Callable

from textual.app import App
from textual.screen import Screen

from battleship.client import get_client
from battleship.engine import session
from battleship.tui import screens


class BattleshipApp(App[None]):
    BINDINGS = [("q", "quit", "Quit"), ("F1", "show_help", "Help")]
    TITLE = "Battleship"
    SUB_TITLE = "The Game"
    CSS_PATH = "styles.tcss"

    def __init__(self, *args: Any, mount_screen: Screen[Any] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._mount_screen = mount_screen or screens.MainMenu()

    def on_mount(self) -> None:
        self.push_screen(self._mount_screen)

    @classmethod
    def singleplayer(
        cls, session_factory: Callable[[], session.SingleplayerSession]
    ) -> "BattleshipApp":
        game_screen = screens.Game(session_factory=session_factory)
        return cls(mount_screen=game_screen)

    async def on_unmount(self) -> None:
        client = get_client()
        await client.disconnect()


if __name__ == "__main__":
    BattleshipApp().run()
