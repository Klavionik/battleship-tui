from textual.app import App

from battleship.client.realtime import get_client
from battleship.tui import screens


class BattleshipApp(App[None]):
    BINDINGS = [("q", "quit", "Quit"), ("F1", "show_help", "Help")]
    TITLE = "Battleship"
    SUB_TITLE = "The Game"
    CSS_PATH = "styles.tcss"

    def on_mount(self) -> None:
        self.push_screen(screens.MainMenu())

    async def on_unmount(self) -> None:
        client = get_client()
        await client.logout()
        await client.disconnect()


if __name__ == "__main__":
    BattleshipApp().run()
