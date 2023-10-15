import enum
import string
from dataclasses import dataclass
from itertools import cycle
from typing import Any, Iterable

from rich.console import Console, ConsoleOptions
from rich.emoji import EMOJI  # type: ignore[attr-defined]
from rich.measure import Measurement
from rich.segment import Segment
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.coordinate import Coordinate
from textual.events import Click, Mount, MouseMove
from textual.message import Message
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import DataTable

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
    direction: Direction = Direction.RIGHT

    def __post_init__(self) -> None:
        self._directions = cycle((Direction.DOWN, Direction.RIGHT))

    def rotate(self) -> None:
        self.direction = next(self._directions)


class MouseButton(enum.IntEnum):
    LEFT = 1
    RIGHT = 3


_cell = " " * 2
_forbidden_cell = Text(_cell, style="on red")
_ship_cell = Text(_cell, style="on green")
_even_cell = Text(_cell, style="on #2D2D2D")
_odd_cell = Text(_cell, style="on #1E1E1E")


@dataclass
class Cell:
    class State(enum.StrEnum):
        EMPTY = "empty"
        FORBIDDEN = "forbidden"
        SHIP = "ship"
        CROSSHAIR = "crosshair"
        MISS = "miss"
        SHIP_DAMAGED = "ship_damaged"
        SHIP_DESTROYED = "ship_destroyed"

    dark: bool = False
    state: State = State.EMPTY

    @classmethod
    def miss(cls, dark: bool = False) -> "Cell":
        return cls(dark, Cell.State.MISS)

    @classmethod
    def damaged(cls, dark: bool = False) -> "Cell":
        return cls(dark, Cell.State.SHIP_DAMAGED)

    @classmethod
    def empty(cls, dark: bool = False) -> "Cell":
        return cls(dark, Cell.State.EMPTY)

    @classmethod
    def ship(cls) -> "Cell":
        return cls(state=Cell.State.SHIP)

    @classmethod
    def forbidden(cls) -> "Cell":
        return cls(state=Cell.State.FORBIDDEN)

    @classmethod
    def crosshair(cls, dark: bool = False) -> "Cell":
        return cls(dark, Cell.State.CROSSHAIR)

    def render(self) -> Text:
        base = _even_cell if self.dark else _odd_cell

        match self.state:
            case Cell.State.EMPTY:
                return base
            case Cell.State.FORBIDDEN:
                return _forbidden_cell
            case Cell.State.SHIP:
                return _ship_cell
            case Cell.State.CROSSHAIR:
                return Text(TARGET, style=base.style)
            case Cell.State.MISS:
                return Text(WATER, style=base.style)
            case Cell.State.SHIP_DAMAGED:
                return Text(FIRE, style=base.style)
            case Cell.State.SHIP_DESTROYED:
                return Text(FIRE, style=base.style)

        return base

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> Iterable[Segment]:
        return self.render().__rich_console__(console, options)

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        return self.render().__rich_measure__(console, options)


class Grid(DataTable[Cell]):
    class GridLeave(Message):
        pass

    def on_leave(self) -> None:
        # Leave event doesn't bubble, thus we need to send a custom event
        self.post_message(self.GridLeave())


class Board(Widget):
    class Mode(enum.StrEnum):
        DISPLAY = "display"
        ARRANGE = "arrange"
        TARGET = "target"

    min_targets: var[int] = var(1)
    mode: var[Mode] = var(Mode.DISPLAY, init=False)

    class ShipPlaced(Message):
        def __init__(self, ship: ShipToPlace, coordinates: list[Coordinate]):
            super().__init__()
            self.ship = ship
            self.coordinates = coordinates

    class CellShot(Message):
        def __init__(self, coordinates: list[Coordinate]):
            super().__init__()
            self.coordinates = coordinates

    def __init__(self, *args: Any, size: int, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.board_size = size
        self._grid = self._create_grid(size)
        self._cursor_coordinate: Coordinate | None = None

        self._ship_to_place: ShipToPlace | None = None
        self._preview_coordinates: list[Coordinate] = []
        self._place_forbidden = True

        self._target_coordinates: list[Coordinate] = []

    @staticmethod
    def detect_cell_coordinate(event: Click | MouseMove) -> Coordinate | None:
        meta = event.style.meta

        try:
            row, column = meta["row"], meta["column"]
        except KeyError:
            # Event outside grid.
            return None

        if row < 0 or column < 0:
            # Event outside cells.
            return None

        return Coordinate(row, column)

    @on(Grid.GridLeave)
    def clean_board(self) -> None:
        self.clean_crosshair()
        self.clean_ship_preview()

    @on(Mount)
    def handle_mount(self) -> None:
        self.initialize_grid()

    @on(MouseMove)
    def handle_mouse_move(self, event: MouseMove) -> None:
        coordinate = self.detect_cell_coordinate(event)

        if self.mode == self.Mode.TARGET:
            self.move_crosshair(coordinate)

        if self.mode == self.Mode.ARRANGE:
            self.move_ship_preview(coordinate)

        self._cursor_coordinate = coordinate

    @on(Click)
    def handle_click(self, event: Click) -> None:
        coordinate = self.detect_cell_coordinate(event)

        if not coordinate:
            return

        if self.mode == self.Mode.TARGET:
            match event.button:
                case MouseButton.LEFT:
                    self.select_target()
                case MouseButton.RIGHT:
                    self.clean_targets()

        if self.mode == self.Mode.ARRANGE:
            match event.button:
                case MouseButton.LEFT:
                    self.place_ship()
                case MouseButton.RIGHT:
                    self.rotate_preview()

    def set_ship_to_place(self, ship: ShipToPlace) -> None:
        self._ship_to_place = ship

    def initialize_grid(self) -> None:
        self._grid.clear()
        self._grid.add_columns(*string.ascii_uppercase[: self.board_size])

        for i, row in enumerate(range(self.board_size), start=1):
            cells = []
            for column in range(self.board_size):
                cells.append(Cell(self.is_dark_cell((row, column))))

            self._grid.add_row(*cells, label=Text(str(i), style="#B0FC38 italic"))

    @staticmethod
    def is_dark_cell(coordinate: tuple[int, int]) -> bool:
        """
        Decide what cell should be at this position. Cell considered
        dark if the sum of its row and column indices is even.

        Args:
            coordinate: A tuple-like object containing a 0-based row index
            and a 0-based column index.
        """
        row, column = coordinate
        row = row + 1
        column = column + 1
        return (row + column) % 2 == 0

    def compose(self) -> ComposeResult:
        yield self._grid

    def move_crosshair(self, coordinate: Coordinate | None) -> None:
        self.clean_crosshair()

        if coordinate:
            self.paint_crosshair(coordinate)

    def is_cell_hit(self, coordinate: Coordinate) -> bool:
        cell = self._grid.get_cell_at(coordinate)
        return cell.state in (Cell.State.MISS, Cell.State.SHIP_DAMAGED, Cell.State.SHIP_DESTROYED)

    def is_cell_ship(self, coordinate: Coordinate) -> bool:
        cell = self._grid.get_cell_at(coordinate)
        return cell.state == Cell.State.SHIP

    def paint_crosshair(self, coordinate: Coordinate) -> None:
        if not self.mode == self.Mode.TARGET:
            return

        if coordinate in self._target_coordinates or self.is_cell_hit(coordinate):
            return

        # Paint crosshair preserving cell's background color.
        self._grid.update_cell_at(coordinate, Cell.crosshair(self.is_dark_cell(coordinate)))

    def clean_crosshair(self) -> None:
        if (
            self._cursor_coordinate
            and self._cursor_coordinate not in self._target_coordinates
            and not self.is_cell_hit(self._cursor_coordinate)
        ):
            self.paint_empty_cell(self._cursor_coordinate)

    def paint_empty_cell(self, coordinate: Coordinate) -> None:
        self._grid.update_cell_at(
            coordinate,
            Cell(self.is_dark_cell(coordinate)),
        )

    def move_ship_preview(self, coordinate: Coordinate | None) -> None:
        # We don't know if we could place the ship
        # after the move, so we forbid it until we know
        # there is enough place.
        self._place_forbidden = True
        self.clean_ship_preview()

        if coordinate:
            self.paint_ship_preview(coordinate.row, coordinate.column)

    def clean_targets(self) -> None:
        while self._target_coordinates:
            coor = self._target_coordinates.pop()
            self.paint_empty_cell(coor)

    def select_target(self) -> None:
        if not self.mode == self.Mode.TARGET:
            return

        if self.is_cell_hit(self._cursor_coordinate):  # type: ignore[arg-type]
            return

        self._target_coordinates.append(
            self._cursor_coordinate,  # type: ignore[arg-type]
        )

        if len(self._target_coordinates) == self.min_targets:
            self.post_message(self.CellShot(self._target_coordinates[:]))
            self.clean_targets()

    def rotate_preview(self) -> None:
        if not self.mode == self.Mode.ARRANGE:
            return

        self._ship_to_place.rotate()  # type: ignore[union-attr]
        self.move_ship_preview(self._cursor_coordinate)

    def clean_ship_preview(self) -> None:
        while self._preview_coordinates:
            coor = self._preview_coordinates.pop()
            self.paint_empty_cell(coor)

    def paint_ship(self, coordinates: Iterable[Coordinate]) -> None:
        for coor in coordinates:
            self._grid.update_cell_at(coor, Cell.ship())

    def paint_forbidden(self, coordinates: Iterable[Coordinate]) -> None:
        for coor in coordinates:
            self._grid.update_cell_at(coor, Cell.forbidden())

    def is_cell_exist(self, coordinate: Coordinate) -> bool:
        return not (
            (coordinate.column >= self.board_size or coordinate.column < 0)
            or (coordinate.row > self.board_size - 1 or coordinate.row < 0)
        )

    def paint_ship_preview(self, row: int, column: int) -> None:
        if self.mode != self.Mode.ARRANGE:
            return

        start = Coordinate(row, column)

        if self.is_cell_ship(start):
            return

        self._preview_coordinates.append(start)

        for _ in range(self._ship_to_place.length - 1):  # type: ignore[union-attr]
            match self._ship_to_place.direction:  # type: ignore[union-attr]
                case Direction.DOWN:
                    next_cell = start.down()
                case Direction.RIGHT:
                    next_cell = start.right()
                case _:
                    return

            if not self.is_cell_exist(next_cell) or self.is_cell_ship(next_cell):
                break

            self._preview_coordinates.append(next_cell)
            start = next_cell
        else:
            self._place_forbidden = False
            self.paint_ship(self._preview_coordinates)
            return

        self.paint_forbidden(self._preview_coordinates)

    def place_ship(self) -> None:
        if self._place_forbidden:
            return

        self.post_message(
            self.ShipPlaced(
                self._ship_to_place,  # type: ignore[arg-type]
                self._preview_coordinates[:],
            )
        )
        self.clean_ship_preview()
        self._ship_to_place = None
        self._place_forbidden = True

    def paint_damage(self, coordinate: Coordinate) -> None:
        self._grid.update_cell_at(coordinate, Cell.damaged(self.is_dark_cell(coordinate)))

    def paint_miss(self, coordinate: Coordinate) -> None:
        self._grid.update_cell_at(coordinate, Cell.miss(self.is_dark_cell(coordinate)))

    def _create_grid(self, size: int) -> Grid:
        # 1. Disable cursor to make Click events bubble up.
        # 2. Disable cell padding to make cells square.
        grid: Grid = Grid(cell_padding=0, cursor_type="none")

        # Size * cell width + row labels width.
        self.styles.width = size * 2 + 2

        # Size + header height.
        self.styles.height = size + 1

        return grid
