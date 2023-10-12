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
from textual.events import Click, Mount, MouseMove
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
        self._directions = cycle((Direction.RIGHT, Direction.DOWN))
        self.direction = next(self._directions)

    def rotate(self) -> None:
        self.direction = next(self._directions)


class MouseButton(enum.IntEnum):
    LEFT = 1
    RIGHT = 3


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
        self._table: DataTable[Text] = DataTable(cell_padding=0, cursor_type="none")
        self._ship_to_place: ShipToPlace | None = None
        self._current_ship_coordinates: list[Coordinate] = []
        self._cursor_coordinate: Coordinate = Coordinate(0, 0)
        self._current_target_coordinates: list[Coordinate] = []
        self._crosshair_coordinate: Coordinate | None = None
        self._place_forbidden = True

        self._cell = " " * 2
        self._forbidden_cell = Text(self._cell, style="on red")
        self._ship_cell = Text(self._cell, style="on green")
        self._even_cell = Text(self._cell, style="on #2D2D2D")
        self._odd_cell = Text(self._cell, style="on #1E1E1E")

    @staticmethod
    def detect_cell_coordinate(event: Click | MouseMove) -> Coordinate | None:
        meta = event.style.meta

        if not meta:
            # Event outside board.
            return None

        row, column = meta["row"], meta["column"]

        if row < 0 or column < 0:
            # Event outside cells.
            return None

        return Coordinate(row, column)

    @on(Mount)
    def handle_mount(self) -> None:
        self.initialize_grid()

    @on(MouseMove)
    def handle_mouse_move(self, event: MouseMove) -> None:
        coordinate = self.detect_cell_coordinate(event)

        if self.mode == self.Mode.TARGET:
            self.move_crosshair(coordinate)

        if self.mode == self.Mode.ARRANGE:
            self.show_preview(coordinate)

    @on(Click)
    def handle_click(self, event: Click) -> None:
        if self.mode == self.Mode.TARGET:
            match event.button:
                case MouseButton.LEFT:
                    self.select_target()
                case MouseButton.RIGHT:
                    self.clear_current_target()

        if self.mode == self.Mode.ARRANGE:
            match event.button:
                case MouseButton.LEFT:
                    self.action_place()
                case MouseButton.RIGHT:
                    self.rotate_preview()

    def set_ship_to_place(self, ship: ShipToPlace) -> None:
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

    def move_crosshair(self, coordinate: Coordinate | None) -> None:
        self.clean_crosshair()

        if coordinate:
            self.paint_crosshair(coordinate)

    def paint_crosshair(self, coordinate: Coordinate) -> None:
        if not self.mode == self.Mode.TARGET:
            return

        if coordinate in self._current_target_coordinates:
            return

        cell = self.get_bg_cell(*coordinate)
        # Paint crosshair preserving cell's background color.
        self._table.update_cell_at(coordinate, value=Text(TARGET, style=cell.style))
        self._crosshair_coordinate = coordinate

    def clean_crosshair(self) -> None:
        if (
            self._crosshair_coordinate
            and self._crosshair_coordinate not in self._current_target_coordinates
        ):
            self._table.update_cell_at(
                self._crosshair_coordinate,
                value=self.get_bg_cell(*self._crosshair_coordinate),
            )
            self._crosshair_coordinate = None

    def show_preview(self, coordinate: Coordinate | None) -> None:
        self._place_forbidden = True

        if coordinate is None:
            self.clear_current_preview()
        else:
            self.preview_ship(coordinate.row, coordinate.column)
            self._cursor_coordinate = coordinate

    def clear_current_target(self) -> None:
        while self._current_target_coordinates:
            coor = self._current_target_coordinates.pop()
            self._table.update_cell_at(
                coor,
                value=self.get_bg_cell(*coor),
            )

    def select_target(self) -> None:
        if not self.mode == self.Mode.TARGET:
            return

        self._current_target_coordinates.append(
            self._crosshair_coordinate,  # type: ignore[arg-type]
        )

        if len(self._current_target_coordinates) == self.min_targets:
            self.emit_cell_shot()
            self.clear_current_target()

    def rotate_preview(self) -> None:
        if not self.mode == self.Mode.ARRANGE:
            return

        self._ship_to_place.rotate()  # type: ignore[union-attr]
        self.preview_ship(*self._cursor_coordinate)

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

        start = Coordinate(row, column)

        if self._table.get_cell_at(start) is self._ship_cell:
            return

        self._current_ship_coordinates.append(start)

        for _ in range(self._ship_to_place.length - 1):  # type: ignore[union-attr]
            match self._ship_to_place.direction:  # type: ignore[union-attr]
                case domain.Direction.DOWN:
                    next_cell = start.down()
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
            # TODO: Fails if clicks happen too fast.
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
