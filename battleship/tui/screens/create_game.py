from typing import Any

from loguru import logger
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import ScreenResume, ScreenSuspend
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Markdown

from battleship.tui import resources
from battleship.tui.widgets import AppFooter
from battleship.tui.widgets.new_game import NewGame


class CreateGame(Screen[None]):
    class CreateMultiplayerSession(Message):
        def __init__(
            self,
            game_name: str,
            roster_name: str,
            firing_order: str,
            salvo_mode: bool,
            no_adjacent_ships: bool,
        ):
            super().__init__()
            self.game_name = game_name
            self.roster_name = roster_name
            self.firing_order = firing_order
            self.salvo_mode = salvo_mode
            self.no_adjacent_ships = no_adjacent_ships

    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with resources.get_resource("create_game_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="container"):
            with VerticalScroll():
                yield Markdown(
                    self.help,
                )

            with Container():
                yield NewGame(with_name=True)

        yield AppFooter()

    def action_back(self) -> None:
        self.app.pop_screen()

    @on(NewGame.PlayPressed)
    def create_session_from_event(self, event: NewGame.PlayPressed) -> None:
        self.post_message(
            self.CreateMultiplayerSession(
                event.name,
                event.roster,
                event.firing_order,
                event.salvo_mode,
                event.no_adjacent_ships,
            )
        )

    @on(ScreenResume)
    def log_enter(self) -> None:
        logger.info("Enter {screen} screen.", screen=self.__class__.__name__)

    @on(ScreenSuspend)
    def log_leave(self) -> None:
        logger.info("Leave {screen} screen.", screen=self.__class__.__name__)
