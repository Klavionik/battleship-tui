from datetime import datetime
from typing import Any, Callable, Iterator

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, RichLog

from battleship.engine import domain, roster, session
from battleship.tui.widgets.board import Board, ShipToPlace


class Game(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(
        self, *args: Any, session_factory: Callable[[], session.SingleplayerSession], **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self._session_factory = session_factory
        self._session = session_factory()
        self.player_board = Board(
            player=self._session.player_name, size=domain.DEFAULT_BOARD_SIZE, classes="player"
        )
        self.enemy_board = Board(
            player=self._session.bot_name, size=domain.DEFAULT_BOARD_SIZE, classes="enemy"
        )
        self.chat = RichLog(wrap=True, markup=True)
        self.ships_to_place: Iterator[roster.RosterItem] = iter(
            [item for item in self._session.roster]
        )

    def compose(self) -> ComposeResult:
        with Horizontal(id="boards"):
            yield self.player_board
            yield self.chat
            yield self.enemy_board

        yield Footer()

    def on_mount(self) -> None:
        self._session.spawn_bot_fleet()
        self.call_later(self.try_ship_placement)

    def get_next_ship_to_place(self) -> roster.RosterItem | None:
        try:
            return next(self.ships_to_place)
        except StopIteration:
            return None

    def write_as_game(self, text: str) -> None:
        now = datetime.now().strftime("%H:%M")
        time = f"[cyan]{now}[/]"
        prefix = "[yellow][Game][/]:"
        self.chat.write(f"{time} {prefix} {text}")

    def try_ship_placement(self) -> None:
        ship = self.get_next_ship_to_place()

        if ship:
            self.write_as_game(f"Place your :ship: [b]{ship.type.title()}[/]")
            self.player_board.ask_placement(ShipToPlace(type=ship.type, length=ship.hp))

    @on(Board.ShipPlaced)
    def spawn_ship(self, event: Board.ShipPlaced) -> None:
        coordinates = event.coordinates
        position = [chr(c.column + 1 + 64) + str(c.row + 1) for c in coordinates]
        self._session.spawn_ship(position, event.ship.type)

        self.try_ship_placement()
