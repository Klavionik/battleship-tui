from typing import Any

import inject
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Markdown

from battleship.engine import create_game
from battleship.engine.rosters import get_roster
from battleship.tui import resources, screens, strategies
from battleship.tui.settings import SettingsProvider
from battleship.tui.widgets import AppFooter
from battleship.tui.widgets.new_game import NewGame


class Singleplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    @inject.param("settings_provider", SettingsProvider)
    def __init__(self, *args: Any, settings_provider: SettingsProvider, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

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

    def start_game(self, roster_name: str, firing_order: str, salvo_mode: bool) -> None:
        roster = get_roster(roster_name)
        game = create_game(
            self._settings.player_name,
            "Computer",
            roster=roster,
            firing_order=firing_order,
            salvo_mode=salvo_mode,
        )
        self.app.push_screen(screens.Game(strategy=strategies.SingleplayerStrategy(game)))

    @on(NewGame.PlayPressed)
    def start_game_from_event(self, event: NewGame.PlayPressed) -> None:
        self.start_game(event.roster, event.firing_order, event.salvo_mode)
