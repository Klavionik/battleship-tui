import dataclasses
import enum
import itertools
import random
import string
from functools import cached_property
from itertools import cycle
from typing import Any, Callable, Collection, Iterable, Iterator

from battleship.engine import errors, roster

DEFAULT_BOARD_SIZE = 10


class Direction(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    RIGHT = "right"
    LEFT = "left"


class FiringOrder(str, enum.Enum):
    ALTERNATELY = "alternately"
    UNTIL_MISS = "until_miss"


@dataclasses.dataclass
class Ship:
    id: str
    type: str
    hp: int
    cells: list[str] = dataclasses.field(default_factory=list, compare=False)

    @property
    def destroyed(self) -> bool:
        return self.hp == 0

    def damage(self) -> None:
        if not self.destroyed:
            self.hp -= 1


@dataclasses.dataclass
class Cell:
    col: str
    row: int
    ship: Ship | None = None
    is_shot: bool = False

    def hit(self) -> None:
        if self.is_shot:
            raise errors.CellAlreadyShot(f"You can't shot the same cell {self} twice.")

        self.is_shot = True

        if self.ship is not None:
            self.ship.damage()

    def set_ship(self, ship: Ship) -> None:
        if self.ship is not None:
            raise errors.CellTaken(f"Cell {self} already has a ship.")

        self.ship = ship

    @property
    def coordinate(self) -> str:
        return f"{self.col}{self.row}"


def parse_coordinate(coordinate: str) -> tuple[str, int]:
    try:
        col, row = coordinate[0], int("".join(coordinate[1:]))
    except (IndexError, TypeError, ValueError):
        raise errors.IncorrectCoordinate(f"Cannot parse coordinate {coordinate}.")

    return col, row


def is_valid_position(coordinates: Iterable[str]) -> None:
    """
    Validates that given coordinates make up either a
    horizontal or a vertical line with no gaps in between.

    Examples:
        A2, A3, A4 is valid. A2, A4, A5 is not.
        B3, C3, D3 is valid. B3, C3, E3 is not.
    """
    parsed_coordinates = [parse_coordinate(coord) for coord in coordinates]
    sorted_coordinates = sorted(parsed_coordinates)

    for curr, next_ in itertools.pairwise(sorted_coordinates):
        curr_col, curr_row = curr
        col_codepoint = ord(curr_col)
        next_valid_hor = chr(col_codepoint + 1), curr_row
        next_valid_ver = chr(col_codepoint), curr_row + 1

        if next_ not in [next_valid_hor, next_valid_ver]:
            raise errors.InvalidPosition(f"Position {coordinates} is invalid.")


class Board:
    def __init__(self, size: int = DEFAULT_BOARD_SIZE) -> None:
        self.size = size
        self._letters = string.ascii_uppercase[:size]
        self._numbers = tuple(range(1, size + 1))
        self.grid = [[Cell(col, row) for col in self._letters] for row in self._numbers]
        self.ships: list[Ship] = []

    def __repr__(self) -> str:
        return f"<Board {self.size}x{self.size}, {len(self.ships)} ships>"

    def __getitem__(self, coordinate: str) -> Cell:
        return self.get_cell(coordinate)

    def _coordinate_to_index(self, coordinate: str) -> tuple[int, int]:
        """
        Coordinate is a string where the zero element is
        a letter in range of the board size and the other elements
        are integers that make up a number in range of the board size.

        :param coordinate: Cell coordinate (like A1, B12, H4 etc.).
        :return: Cell cols index and cell row index.
        """
        col, row = parse_coordinate(coordinate)

        try:
            col_index = self._letters.index(col)
        except ValueError:
            raise errors.CellOutOfRange(f"No column {col} in range {self._letters}.")

        try:
            row_index = self._numbers.index(row)
        except ValueError:
            raise errors.CellOutOfRange(f"No row {row} in range {self._numbers}.")

        return col_index, row_index

    @cached_property
    def cells(self) -> list[Cell]:
        return [cell for row in self.grid for cell in row]

    def get_adjacent_cell(self, cell: Cell, direction: Direction) -> Cell | None:
        coordinate = ""

        match direction:
            case Direction.UP:
                coordinate = f"{cell.col}{cell.row - 1}"
            case Direction.DOWN:
                coordinate = f"{cell.col}{cell.row + 1}"
            case Direction.RIGHT:
                coordinate = f"{chr(ord(cell.col) + 1)}{cell.row}"
            case Direction.LEFT:
                coordinate = f"{chr(ord(cell.col) - 1)}{cell.row}"

        try:
            return self.get_cell(coordinate)
        except errors.CellOutOfRange:
            return None

    def get_cell(self, coordinate: str) -> Cell:
        col, row = self._coordinate_to_index(coordinate)
        return self.grid[row][col]

    def place_ship(self, position: Collection[str], ship: Ship) -> None:
        if len(position) != ship.hp:
            raise errors.ShipDoesntFitCells(
                f"Cannot place {ship.hp} HP ship onto {len(position)} cells."
            )

        is_valid_position(position)

        for coordinate in position:
            self.get_cell(coordinate).set_ship(ship)

        self.ships.append(ship)
        ship.cells.extend(position)

    def hit_cell(self, coordinate: str) -> Ship | None:
        cell = self.get_cell(coordinate)
        cell.hit()
        return cell.ship


@dataclasses.dataclass(unsafe_hash=True)
class Player:
    name: str
    board: Board = dataclasses.field(default_factory=Board, hash=False)

    def __repr__(self) -> str:
        return self.name

    def add_ship(self, position: Collection[str], ship: Ship) -> None:
        self.board.place_ship(position, ship)

    def attack(self, coordinate: str) -> Ship | None:
        return self.board.hit_cell(coordinate)

    def count_ships(self, ship_type: roster.ShipType) -> int:
        return len([ship for ship in self.board.ships if ship.type == ship_type])

    def get_ship(self, ship_id: str) -> Ship | None:
        try:
            return next(ship for ship in self.ships if ship.id == ship_id)
        except StopIteration:
            return None

    @property
    def ships_alive(self) -> int:
        return len([ship for ship in self.board.ships if not ship.destroyed])

    @property
    def ships(self) -> list[Ship]:
        return self.board.ships


@dataclasses.dataclass
class Shot:
    coordinate: str
    hit: bool
    ship: Ship | None

    @property
    def miss(self) -> bool:
        return not self.hit


@dataclasses.dataclass
class Salvo:
    actor: Player
    subject: Player
    shots: list[Shot] = dataclasses.field(default_factory=list)

    @property
    def miss(self) -> bool:
        return all(shot.miss for shot in self)

    @property
    def ships_left(self) -> int:
        return self.subject.ships_alive

    def add_shot(self, shot: Shot) -> None:
        self.shots.append(shot)

    def __len__(self) -> int:
        return len(self.shots)

    def __iter__(self) -> Iterator[Shot]:
        return iter(self.shots)


class Hook(str, enum.Enum):
    SHIP_ADDED = "ship_added"
    FLEET_READY = "fleet_ready"
    NEXT_MOVE = "next_move"
    GAME_ENDED = "game_ended"


class Game:
    def __init__(
        self,
        player_a: Player,
        player_b: Player,
        roster: roster.Roster,
        firing_order: FiringOrder = FiringOrder.ALTERNATELY,
        salvo_mode: bool = False,
    ) -> None:
        self.player_a = player_a
        self.player_b = player_b
        self.roster = roster
        self.firing_order = firing_order
        self.salvo_mode = salvo_mode

        self._players = {player_a, player_b}
        self._player_cycle = cycle(random.sample([player_a, player_b], k=2))
        self._current_player = next(self._player_cycle)
        self._started = False
        self._winner: Player | None = None
        self._hooks: dict[Hook, Callable[..., Any] | None] = dict.fromkeys(Hook, None)
        self._make_turn = False

    def __str__(self) -> str:
        return f"Game <{self.player_a} vs {self.player_b}> <Winner: {self._winner}>"

    def add_ship(self, player: Player, position: Collection[str], roster_id: roster.ShipId) -> None:
        if player.get_ship(roster_id) is None:
            ship = self._build_ship(roster_id)
            player.add_ship(position, ship)
        else:
            raise errors.ShipLimitExceeded(
                f"Player {player.name} already has a ship with roster id {roster_id}."
            )

        if ship_added_hook := self._hooks[Hook.SHIP_ADDED]:
            ship_added_hook(player, roster_id, position)

        if self.is_fleet_ready(player) and (fleet_ready_hook := self._hooks[Hook.FLEET_READY]):
            fleet_ready_hook(player)

        if self.ready and (next_move_hook := self._hooks[Hook.NEXT_MOVE]):
            next_move_hook(self)

    def register_hook(self, name: Hook, hook: Callable[..., Any]) -> None:
        if not callable(hook):
            raise TypeError("Hook must be a callable.")

        self._hooks[name] = hook

    def clear_hooks(self) -> None:
        self._hooks.clear()

    def is_fleet_ready(self, player: Player) -> bool:
        return {ship.id for ship in player.ships} == {item.id for item in self.roster}

    def _build_ship(self, ship_id: roster.ShipId) -> Ship:
        try:
            item = self.roster[ship_id]
            return Ship(*item)
        except KeyError:
            raise errors.ShipNotFound(f"No ship with ID {ship_id} in the roster.")

    @property
    def current_player(self) -> Player:
        return self._current_player

    @property
    def player_under_attack(self) -> Player:
        return (self._players - {self.current_player}).pop()

    @property
    def winner(self) -> Player | None:
        return self._winner

    @property
    def ready(self) -> bool:
        return self.is_fleet_ready(self.player_a) and self.is_fleet_ready(self.player_b)

    def fire(self, coordinates: Collection[str]) -> Salvo:
        if not self.ready:
            raise errors.GameNotReady("Place all ships before firing.")

        if self.winner:
            raise errors.GameEnded(f"{self.winner} won this game.")

        if len(coordinates) > 1 and not self.salvo_mode:
            raise errors.TooManyShots("Multiple shots in one turn permitted only in salvo mode.")

        if self.salvo_mode and (len(coordinates) != self.current_player.ships_alive):
            raise errors.IncorrectShots(
                f"Number of shots {len(coordinates)} must be equal "
                f"to the number of alive ships {self.current_player.ships_alive}."
            )

        salvo = Salvo(
            actor=self.current_player,
            subject=self.player_under_attack,
        )

        for coordinate in coordinates:
            maybe_ship = self.player_under_attack.attack(coordinate)
            shot = Shot(
                coordinate=coordinate,
                hit=maybe_ship is not None,
                ship=maybe_ship,
            )
            salvo.add_shot(shot)

        self._make_turn = True
        return salvo

    def turn(self, salvo: Salvo) -> None:
        if not self._make_turn:
            raise RuntimeError("Cannot make turn at this time. Try calling fire() before.")

        if self.player_under_attack.ships_alive == 0:
            self._winner = self.current_player

            if ended_hook := self._hooks[Hook.GAME_ENDED]:
                ended_hook(self)
        else:
            if (
                self.firing_order == FiringOrder.ALTERNATELY
                or self.firing_order == FiringOrder.UNTIL_MISS
                and salvo.miss
            ):
                self._current_player = next(self._player_cycle)

            if next_move_hook := self._hooks[Hook.NEXT_MOVE]:
                next_move_hook(self)

        self._make_turn = False
