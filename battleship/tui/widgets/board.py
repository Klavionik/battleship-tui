import string
from dataclasses import dataclass
from enum import IntEnum, auto
from itertools import cycle
from typing import Any, Iterable

from loguru import logger
from rich.console import Console, ConsoleOptions
from rich.emoji import EMOJI  # type: ignore[attr-defined]
from rich.measure import Measurement
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.coordinate import Coordinate
from textual.events import Click, Mount, MouseMove
from textual.message import Message
from textual.reactive import reactive, var
from textual.widget import Widget
from textual.widgets import DataTable, Label

from battleship.engine.domain import Direction
from battleship.shared.compat import StrEnum

WATER = EMOJI["water_wave"]
FIRE = EMOJI["fire"]
TARGET = EMOJI["dart"]
CROSSMARK = EMOJI["cross_mark"]
MAN = EMOJI["man"]


@dataclass
class ShipToPlace:
    id: str
    hp: int
    direction: Direction = Direction.RIGHT

    def __post_init__(self) -> None:
        self._directions = cycle((Direction.DOWN, Direction.RIGHT))

    def rotate(self) -> None:
        self.direction = next(self._directions)


class MouseButton(IntEnum):
    LEFT = 1
    RIGHT = 3


@dataclass
class CellFactory:
    cell_width: int = 2
    light_bg: str = "#2D2D2D"
    dark_bg: str = "#1E1E1E"
    forbidden_bg: str = "#ba3c5b"
    ship_bg: str = "green"
    miss_value: str = WATER
    crosshair_value: str = TARGET
    damaged_value: str = FIRE
    destroyed_value: str = CROSSMARK

    @property
    def empty_value(self) -> str:
        return " " * self.cell_width

    def get_bg(self, dark: bool) -> str:
        return self.dark_bg if dark else self.light_bg

    def miss(self, dark: bool = False) -> "Cell":
        return Cell(self.miss_value, self.get_bg(dark), Cell.Type.MISS)

    def damaged(self) -> "Cell":
        return Cell(self.damaged_value, self.ship_bg, Cell.Type.SHIP_DAMAGED)

    def destroyed(self) -> "Cell":
        return Cell(self.destroyed_value, self.ship_bg, Cell.Type.SHIP_DESTROYED)

    def empty(self, dark: bool = False) -> "Cell":
        return Cell(self.empty_value, self.get_bg(dark), Cell.Type.EMPTY)

    def ship(self) -> "Cell":
        return Cell(self.empty_value, self.ship_bg, Cell.Type.SHIP)

    def forbidden(self) -> "Cell":
        return Cell(self.empty_value, self.forbidden_bg, Cell.Type.FORBIDDEN)

    def crosshair(self, dark: bool = False) -> "Cell":
        return Cell(self.crosshair_value, self.get_bg(dark), Cell.Type.CROSSHAIR)


@dataclass
class Cell:
    class Type(StrEnum):
        EMPTY = auto()
        FORBIDDEN = auto()
        SHIP = auto()
        CROSSHAIR = auto()
        MISS = auto()
        SHIP_DAMAGED = auto()
        SHIP_DESTROYED = auto()

    value: str
    bg: str
    type: Type

    def render(self) -> Text:
        return Text(self.value, Style(bgcolor=self.bg))

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> Iterable[Segment]:
        return self.render().__rich_console__(console, options)

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        return self.render().__rich_measure__(console, options)


class Grid(DataTable[Cell]):
    class GridLeave(Message):
        pass

    def on_leave(self) -> None:
        # Leave type doesn't bubble, thus we need to send a custom type
        self.post_message(self.GridLeave())


class PlayerName(Label):
    show_fire: reactive[bool] = reactive(False)

    def __init__(self, *args: Any, value: str, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._value = value

    def watch_show_fire(self, value: bool) -> None:
        self.log.warning(f"{value=}")

        if value:
            name = f"{self._value} [red bold blink]FIRE[/]"
        else:
            name = self._value

        self.update(f"{MAN} {name}")


class Board(Widget):
    class Mode(StrEnum):
        DISPLAY = auto()
        ARRANGE = auto()
        TARGET = auto()

    min_targets: var[int] = var(1)
    mode: var[Mode] = var(Mode.DISPLAY, init=False)
    under_attack: reactive[bool] = reactive(False)

    class ShipPlaced(Message):
        def __init__(self, ship: ShipToPlace, coordinates: list[Coordinate]):
            super().__init__()
            self.ship = ship
            self.coordinates = coordinates

    class CellShot(Message):
        def __init__(self, coordinates: list[Coordinate]):
            super().__init__()
            self.coordinates = coordinates

    def __init__(
        self, *args: Any, player_name: str, size: int, cell_factory: CellFactory, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.player_name = player_name
        self.board_size = size
        self._cell_factory = cell_factory
        # 1. Disable cursor to make Click events bubble up.
        # 2. Disable cell padding to make cells square.
        self._grid = Grid(cell_padding=0, cursor_type="none")
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
        if self.mode == self.Mode.DISPLAY:
            return

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

    def show_ship_preview(self, ship_id: str, ship_hp: int) -> None:
        self._ship_to_place = ShipToPlace(ship_id, ship_hp)

    def initialize_grid(self) -> None:
        self._grid.clear()
        self._grid.add_columns(*string.ascii_uppercase[: self.board_size])

        for i, row in enumerate(range(self.board_size), start=1):
            cells = []
            for column in range(self.board_size):
                dark = self.is_dark_cell((row, column))
                cells.append(self._cell_factory.empty(dark))

            self._grid.add_row(*cells, label=Text(str(i)))

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
        yield PlayerName(value=self.player_name).data_bind(show_fire=Board.under_attack)
        yield self._grid

    def move_crosshair(self, coordinate: Coordinate | None) -> None:
        self.clean_crosshair()

        if coordinate:
            self.paint_crosshair(coordinate)

    def is_cell_hit(self, coordinate: Coordinate) -> bool:
        cell = self._grid.get_cell_at(coordinate)
        return cell.type in (Cell.Type.MISS, Cell.Type.SHIP_DAMAGED, Cell.Type.SHIP_DESTROYED)

    def is_cell_ship(self, coordinate: Coordinate) -> bool:
        cell = self._grid.get_cell_at(coordinate)
        return cell.type == Cell.Type.SHIP

    def paint_crosshair(self, coordinate: Coordinate) -> None:
        if not self.mode == self.Mode.TARGET:
            return

        if coordinate in self._target_coordinates or self.is_cell_hit(coordinate):
            return

        # Paint crosshair preserving cell's background color.
        crosshair = self._cell_factory.crosshair((self.is_dark_cell(coordinate)))
        self._grid.update_cell_at(coordinate, crosshair)

    def clean_crosshair(self) -> None:
        if (
            self._cursor_coordinate
            and self._cursor_coordinate not in self._target_coordinates
            and not self.is_cell_hit(self._cursor_coordinate)
        ):
            self.paint_empty_cell(self._cursor_coordinate)

    def paint_empty_cell(self, coordinate: Coordinate) -> None:
        empty = self._cell_factory.empty(self.is_dark_cell(coordinate))
        self._grid.update_cell_at(coordinate, empty)

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

        if self._cursor_coordinate is None:
            logger.warning("Trying to select target w/o a cursor.")
            return

        cell_targeted = self._cursor_coordinate in self._target_coordinates
        cell_hit = self.is_cell_hit(self._cursor_coordinate)

        if cell_hit or cell_targeted:
            return

        self._target_coordinates.append(self._cursor_coordinate)

        if len(self._target_coordinates) == self.min_targets:
            self.post_message(self.CellShot(self._target_coordinates[:]))
            self.clean_targets()

    def rotate_preview(self) -> None:
        if not self.mode == self.Mode.ARRANGE:
            return

        assert self._ship_to_place, "No ship to rotate"

        self._ship_to_place.rotate()
        self.move_ship_preview(self._cursor_coordinate)

    def clean_ship_preview(self) -> None:
        while self._preview_coordinates:
            coor = self._preview_coordinates.pop()
            self.paint_empty_cell(coor)

    def paint_ship(self, coordinates: Iterable[Coordinate]) -> None:
        for coor in coordinates:
            self._grid.update_cell_at(coor, self._cell_factory.ship())

    def paint_forbidden(self, coordinates: Iterable[Coordinate]) -> None:
        for coor in coordinates:
            self._grid.update_cell_at(coor, self._cell_factory.forbidden())

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

        assert self._ship_to_place, "Trying to display ship preview w/o ship"

        for _ in range(self._ship_to_place.hp - 1):
            match self._ship_to_place.direction:
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

        assert self._ship_to_place, "Trying to place ship w/o ship set"

        self.post_message(
            self.ShipPlaced(
                self._ship_to_place,
                self._preview_coordinates[:],
            )
        )
        self.clean_ship_preview()
        self._ship_to_place = None
        self._place_forbidden = True

    def paint_damage(self, coordinate: Coordinate) -> None:
        self._grid.update_cell_at(coordinate, self._cell_factory.damaged())

    def paint_miss(self, coordinate: Coordinate) -> None:
        miss = self._cell_factory.miss(self.is_dark_cell(coordinate))
        self._grid.update_cell_at(coordinate, miss)

    def paint_destroyed(self, coordinates: Iterable[Coordinate]) -> None:
        for coor in coordinates:
            destroyed = self._cell_factory.destroyed()
            self._grid.update_cell_at(coor, destroyed)
