from textual.app import App

from battleship.tui import screens


class BattleshipApp(App[None]):
    BINDINGS = [("ctrl+q", "quit", "Quit"), ("F1", "show_help", "Help")]
    TITLE = "Battleship"
    SUB_TITLE = "The Game"
    CSS_PATH = "styles.tcss"

    def on_mount(self) -> None:
        self.push_screen(screens.MainMenu())
