from typing import Any

from loguru import logger
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import ScreenResume, ScreenSuspend
from textual.screen import Screen
from textual.widgets import Markdown

from battleship.engine import create_game
from battleship.engine.rosters import get_roster
from battleship.tui import resources, screens, strategies
from battleship.tui.di import container
from battleship.tui.settings import SettingsProvider
from battleship.tui.widgets import AppFooter
from battleship.tui.widgets.new_game import NewGame


class Singleplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        settings_provider = container.resolve(SettingsProvider)
        self._settings = settings_provider.load()

        with resources.get_resource("singleplayer_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="container"):
            with VerticalScroll():
                yield Markdown(
                    self.help,
                )

            with Container():
                yield NewGame()

        yield AppFooter()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    def start_game(
        self, roster_name: str, firing_order: str, salvo_mode: bool, no_adjacent_ships: bool
    ) -> None:
        roster = get_roster(roster_name)
        game = create_game(
            self._settings.player_name,
            "Computer",
            roster=roster,
            firing_order=firing_order,
            salvo_mode=salvo_mode,
            no_adjacent_ships=no_adjacent_ships,
        )
        logger.info(
            "Start singleplayer game. Player name: {player_name}. Roster: {roster}. "
            "Firing order: {firing_order}. Salvo mode: {salvo_mode}. "
            "No adjacent ships: {no_adjacent_ships}.",
            player_name=self._settings.player_name,
            roster=roster,
            firing_order=firing_order,
            salvo_mode=salvo_mode,
            no_adjacent_ships=no_adjacent_ships,
        )
        self.app.push_screen(screens.Game(strategy=strategies.SingleplayerStrategy(game)))

    @on(NewGame.PlayPressed)
    def start_game_from_event(self, event: NewGame.PlayPressed) -> None:
        self.start_game(event.roster, event.firing_order, event.salvo_mode, event.no_adjacent_ships)

    @on(ScreenResume)
    def log_enter(self) -> None:
        logger.info("Enter {screen} screen.", screen=self.__class__.__name__)

    @on(ScreenSuspend)
    def log_leave(self) -> None:
        logger.info("Leave {screen} screen.", screen=self.__class__.__name__)
