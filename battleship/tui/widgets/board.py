import string
from dataclasses import dataclass
from itertools import cycle
from typing import Any, Iterable

from rich.emoji import EMOJI  # type: ignore[attr-defined]
from rich.text import Text
from textual.app import ComposeResult
from textual.coordinate import Coordinate
from textual.events import MouseMove
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Static

from battleship.engine import domain
from battleship.engine.domain import Direction

SHIP = EMOJI["ship"]
WATER = EMOJI["water_wave"]
FIRE = EMOJI["fire"]
CROSS = EMOJI["cross_mark"]


@dataclass
class ShipToPlace:
    type: str
    length: int
    direction: str = ""

    def __post_init__(self) -> None:
        self._directions = cycle((Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT))
        self.direction = next(self._directions)

    def rotate(self) -> None:
        self.direction = next(self._directions)


class Board(Widget):
    BINDINGS = [
        ("r", "rotate", "Rotate ship"),
        ("space", "place", "Place ship"),
    ]
    DEFAULT_CSS = """
    Board {
      width: 1fr;
    }
    """

    class ShipPlaced(Message):
        def __init__(self, ship: ShipToPlace, coordinates: list[Coordinate]):
            super().__init__()
            self.ship = ship
            self.coordinates = coordinates

    def __init__(self, *args: Any, player: str, size: int, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.player = player
        self.board_size = size
        self._table: DataTable[Text] = DataTable(cell_padding=0)
        self._ship_to_place: ShipToPlace | None = None
        self._current_ship_coordinates: list[Coordinate] = []
        self._place_forbidden = True

        self._cell = " " * 2
        self._forbidden_cell = Text(self._cell, style="on red")
        self._ship_cell = Text(self._cell, style="on green")
        self._even_cell = Text(self._cell, style="on #2D2D2D")
        self._odd_cell = Text(self._cell, style="on #1E1E1E")

    def on_mount(self) -> None:
        self.initialize_grid()

    def ask_placement(self, ship: ShipToPlace) -> None:
        self._ship_to_place = ship

    def initialize_grid(self) -> None:
        self._table.clear()
        self._table.add_columns(*string.ascii_uppercase[: self.board_size])

        for i, row in enumerate(range(self.board_size), start=1):
            cells = []
            for column in range(self.board_size):
                cells.append(self.get_bg_cell(row, column))

            self._table.add_row(*cells, label=Text(str(i), style="#B0FC38 italic"))

    def get_bg_cell(self, row: int, column: int) -> Text:
        """
        Decide what cell should be at this position.

        Args:
            row: 0-based row index.
            column: 0-based column index.

        Returns: Even cell or odd cell.

        """
        row, column = row + 1, column + 1
        # Cell considered even if the sum of its row and column indices is even.
        is_cell_even = (row + column) % 2 == 0
        return self._even_cell if is_cell_even else self._odd_cell

    def compose(self) -> ComposeResult:
        yield Static(self.player)
        yield self._table

    def on_mouse_move(self, event: MouseMove) -> None:
        self._place_forbidden = True

        try:
            row, column = event.style.meta["row"], event.style.meta["column"]
        except KeyError:
            # Cursor outside grid, clear preview.
            self.clear_current_preview()
        else:
            self.preview_ship(row, column)

    def action_rotate(self) -> None:
        if not self._ship_to_place:
            return

        self._ship_to_place.rotate()
        self.preview_ship(*self._table.hover_coordinate)

    def clear_current_preview(self) -> None:
        while self._current_ship_coordinates:
            coor = self._current_ship_coordinates.pop()
            self._table.update_cell_at(coor, value=self.get_bg_cell(coor.row, coor.column))

    def place_ship(self, coordinates: Iterable[Coordinate]) -> None:
        for coor in coordinates:
            self._table.update_cell_at(coor, value=self._ship_cell)

    def is_coordinate_outside_board(self, coordinate: Coordinate) -> bool:
        return (coordinate.column >= self.board_size or coordinate.column < 0) or (
            coordinate.row > self.board_size - 1 or coordinate.row < 0
        )

    def preview_ship(self, row: int, column: int) -> None:
        if self._ship_to_place is None:
            return

        self.clear_current_preview()

        if row < 0 or column < 0:
            # Cursor outside grid.
            return

        start = Coordinate(row, column)

        if self._table.get_cell_at(start) is self._ship_cell:
            return

        self._current_ship_coordinates.append(start)

        for _ in range(self._ship_to_place.length - 1):
            match self._ship_to_place.direction:
                case domain.Direction.DOWN:
                    next_cell = start.down()
                case domain.Direction.UP:
                    next_cell = start.up()
                case domain.Direction.LEFT:
                    next_cell = start.left()
                case domain.Direction.RIGHT:
                    next_cell = start.right()
                case _:
                    return

            if self.is_coordinate_outside_board(next_cell):
                break

            if self._table.get_cell_at(next_cell) is self._ship_cell:
                break

            self._current_ship_coordinates.append(next_cell)
            start = next_cell
        else:
            self._place_forbidden = False
            self.place_ship(self._current_ship_coordinates)
            return

        for coor in self._current_ship_coordinates:
            self._table.update_cell_at(coor, value=self._forbidden_cell)

    def action_place(self) -> None:
        if self._place_forbidden or not self._ship_to_place:
            return

        self.place_ship(self._current_ship_coordinates)
        self.post_message(self.ShipPlaced(self._ship_to_place, self._current_ship_coordinates[:]))
        self._current_ship_coordinates.clear()
        self._ship_to_place = None

    def update_grid(self, board: domain.Board) -> None:
        table = self.query_one(DataTable)
        table.clear()

        for number, row in enumerate(board.grid, start=1):
            label = Text(str(number), style="#B0FC38 italic")
            cells = []

            for cell in row:
                if cell.ship is not None:
                    if cell.is_shot:
                        cells.append(FIRE)
                    else:
                        cells.append(SHIP)
                else:
                    if cell.is_shot:
                        cells.append(WATER)
                    else:
                        cells.append("")

            table.add_row(*cells, label=label)
