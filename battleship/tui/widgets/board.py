import enum
import string
from dataclasses import dataclass
from itertools import cycle
from typing import Any, Iterable

from rich.emoji import EMOJI  # type: ignore[attr-defined]
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.coordinate import Coordinate
from textual.events import MouseMove
from textual.message import Message
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import DataTable, Static

from battleship.engine import domain
from battleship.engine.domain import Direction

SHIP = EMOJI["ship"]
WATER = EMOJI["water_wave"]
FIRE = EMOJI["fire"]
CROSS = EMOJI["cross_mark"]
TARGET = EMOJI["dart"]


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
    class Mode(enum.StrEnum):
        NONE = "none"
        ARRANGE = "arrange"
        TARGET = "target"

    DEFAULT_CSS = """
    Board {
      width: 1fr;
    }
    """
    min_targets: var[int] = var(1)
    mode: var[Mode] = var(Mode.NONE, init=False)

    class ShipPlaced(Message):
        def __init__(self, ship: ShipToPlace, coordinates: list[Coordinate]):
            super().__init__()
            self.ship = ship
            self.coordinates = coordinates

    class CellShot(Message):
        def __init__(self, coordinates: list[Coordinate]):
            super().__init__()
            self.coordinates = coordinates

    def __init__(self, *args: Any, player: str, size: int, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.player = player
        self.board_size = size
        self._table: DataTable[Text] = DataTable(cell_padding=0)
        self._ship_to_place: ShipToPlace | None = None
        self._current_ship_coordinates: list[Coordinate] = []
        self._current_target_coordinates: list[Coordinate] = []
        self._last_target_coordinate: Coordinate | None = None
        self._place_forbidden = True

        self._cell = " " * 2
        self._forbidden_cell = Text(self._cell, style="on red")
        self._ship_cell = Text(self._cell, style="on green")
        self._even_cell = Text(self._cell, style="on #2D2D2D")
        self._odd_cell = Text(self._cell, style="on #1E1E1E")

    def key_r(self) -> None:
        self.rotate_preview()

    def key_space(self) -> None:
        self.action_place()

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

    def show_preview(self, event: MouseMove) -> None:
        self._place_forbidden = True

        try:
            row, column = event.style.meta["row"], event.style.meta["column"]
        except KeyError:
            # Cursor outside grid, clear preview.
            self.clear_current_preview()
        else:
            self.preview_ship(row, column)

    def clear_current_target(self) -> None:
        while self._current_target_coordinates:
            coor = self._current_target_coordinates.pop()
            self._table.update_cell_at(
                coor,
                value=self.get_bg_cell(*coor),
            )

    def clear_last_target(self) -> None:
        if (
            self._last_target_coordinate
            and self._last_target_coordinate not in self._current_target_coordinates
        ):
            self._table.update_cell_at(
                self._last_target_coordinate, value=self.get_bg_cell(*self._last_target_coordinate)
            )

    @on(DataTable.CellSelected)
    def select_target(self, event: DataTable.CellSelected) -> None:
        event.stop()

        if not self.mode == self.Mode.TARGET:
            return

        self._current_target_coordinates.append(event.coordinate)

        if len(self._current_target_coordinates) == self.min_targets:
            self.emit_cell_shot()
            self.clear_current_target()

    def target_cell(self, row: int, column: int) -> None:
        if not self.mode == self.Mode.TARGET:
            return

        if row < 0 or column < 0:
            # Cursor inside table, but outside cells.
            return

        coordinate = Coordinate(row, column)

        if coordinate in self._current_target_coordinates:
            return

        cell = self.get_bg_cell(row, column)
        # Paint target symbol preserving cell's background color.
        self._table.update_cell_at(coordinate, value=Text(TARGET, style=cell.style))
        self._last_target_coordinate = coordinate

    def show_target(self, event: MouseMove) -> None:
        self.clear_last_target()

        try:
            row, column = event.style.meta["row"], event.style.meta["column"]
        except KeyError:
            # Cursor outside grid.
            self.clear_last_target()
        else:
            self.target_cell(row, column)

    def on_mouse_move(self, event: MouseMove) -> None:
        if self.mode == self.Mode.TARGET:
            self.show_target(event)
        else:
            self.show_preview(event)

    def rotate_preview(self) -> None:
        if not self.mode == self.Mode.ARRANGE:
            return

        self._ship_to_place.rotate()  # type: ignore[union-attr]
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

    def emit_cell_shot(self) -> None:
        self.post_message(self.CellShot(self._current_target_coordinates[:]))

    def preview_ship(self, row: int, column: int) -> None:
        if self.mode != self.Mode.ARRANGE:
            return

        self.clear_current_preview()

        if row < 0 or column < 0:
            # Cursor outside grid.
            return

        start = Coordinate(row, column)

        if self._table.get_cell_at(start) is self._ship_cell:
            return

        self._current_ship_coordinates.append(start)

        for _ in range(self._ship_to_place.length - 1):  # type: ignore[union-attr]
            match self._ship_to_place.direction:  # type: ignore[union-attr]
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
        # TODO: Do I really need the second condition?
        if self._place_forbidden or self.mode != self.Mode.ARRANGE:
            return

        self.place_ship(self._current_ship_coordinates)
        self.post_message(
            self.ShipPlaced(
                self._ship_to_place,  # type: ignore[arg-type]
                self._current_ship_coordinates[:],
            )
        )
        self._current_ship_coordinates.clear()
        self._ship_to_place = None
