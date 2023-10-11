from typing import Any, Callable

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, RichLog

from battleship.engine import domain
from battleship.tui.widgets.board import Board


class Game(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, game_factory: Callable[[], domain.Game], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._game_factory = game_factory
        self._game = game_factory()
        self._boards = {
            player: Board(player=player.name, size=player.board.size, roster=self._game.roster)
            for player in self._game.players
        }

    def compose(self) -> ComposeResult:
        yield from self._boards.values()
        yield RichLog()
        yield Footer()
