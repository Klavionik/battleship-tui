import dataclasses
import enum
import itertools
import random
import string
from functools import cached_property
from itertools import cycle
from typing import Collection, Iterable, Iterator

from battleship.engine import errors, roster

DEFAULT_BOARD_SIZE = 10


class Direction(enum.StrEnum):
    UP = "up"
    DOWN = "down"
    RIGHT = "right"
    LEFT = "left"


class FiringOrder(enum.StrEnum):
    ALTERNATELY = "alternately"
    UNTIL_MISS = "until_miss"


@dataclasses.dataclass
class Ship:
    type: str
    hp: int

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

    def hit_cell(self, coordinate: str) -> Ship | None:
        cell = self.get_cell(coordinate)
        cell.hit()
        return cell.ship


@dataclasses.dataclass(unsafe_hash=True)
class Player:
    name: str
    board: Board = dataclasses.field(default_factory=Board, hash=False)

    def add_ship(self, position: Collection[str], ship: Ship) -> None:
        self.board.place_ship(position, ship)

    def attack(self, coordinate: str) -> Ship | None:
        return self.board.hit_cell(coordinate)

    def count_ships(self, ship_type: roster.ShipType) -> int:
        return len([ship for ship in self.board.ships if ship.type == ship_type])

    @property
    def ships_alive(self) -> int:
        return len([ship for ship in self.board.ships if not ship.destroyed])

    @property
    def ships(self) -> list[Ship]:
        return self.board.ships


@dataclasses.dataclass
class Shot:
    coordinate: str
    ship: Ship | None

    @property
    def hit(self) -> bool:
        return not self.miss

    @property
    def miss(self) -> bool:
        return self.ship is None


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


class Game:
    def __init__(
        self,
        player_a: Player,
        player_b: Player,
        roster: roster.Roster,
        firing_order: FiringOrder = FiringOrder.ALTERNATELY,
        salvo_mode: bool = False,
    ) -> None:
        self.players = {player_a, player_b}
        self.roster = roster
        self.firing_order = firing_order
        self.salvo_mode = salvo_mode
        self._player_a = player_a
        self._player_b = player_b
        self._reference_fleet = [Ship(item.type, item.hp) for item in roster.items]
        self._player_cycle = cycle(random.sample([player_a, player_b], k=2))
        self._current_player = next(self._player_cycle)
        self._started = False
        self._winner: Player | None = None

    def __str__(self) -> str:
        return f"Game <{self._player_a} vs {self._player_b}> <Winner: {self._winner}>"

    def add_ship(
        self, player: Player, position: Collection[str], ship_type: roster.ShipType
    ) -> None:
        ship = self._spawn_ship(ship_type)
        max_ships = self._max_ships_for_type(ship_type)

        if player.count_ships(ship_type) >= max_ships:
            raise errors.ShipLimitExceeded(
                f"You can put only {max_ships} ships of type {ship_type}."
            )

        player.add_ship(position, ship)

    def is_fleet_ready(self, player: Player) -> bool:
        return player.ships == self._reference_fleet

    def _spawn_ship(self, ship_type: roster.ShipType) -> Ship:
        try:
            roster_item = next(item for item in self.roster.items if item.type == ship_type)
            return Ship(*roster_item)
        except StopIteration:
            raise errors.ShipNotFound(f"No ship of type {ship_type} in the roster.")

    def _max_ships_for_type(self, ship_type: roster.ShipType) -> int:
        return len([ship for ship in self._reference_fleet if ship.type == ship_type])

    @property
    def current_player(self) -> Player:
        return self._current_player

    @property
    def player_under_attack(self) -> Player:
        return (self.players - {self.current_player}).pop()

    @property
    def winner(self) -> Player | None:
        return self._winner

    @property
    def started(self) -> bool:
        return self._started

    @property
    def ended(self) -> bool:
        return self._winner is not None

    def start(self) -> None:
        if not (self.is_fleet_ready(self._player_a) and self.is_fleet_ready(self._player_b)):
            raise errors.ShipsNotPlaced("There are still some ships to be placed before start.")

        self._started = True

    def fire(self, coordinates: Collection[str]) -> Salvo:
        if not self._started:
            raise errors.GameNotStarted("Place ships and call `start()` before firing.")

        if self.ended:
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
                ship=maybe_ship,
            )
            salvo.add_shot(shot)

        if self.player_under_attack.ships_alive == 0:
            self._winner = self.current_player
            return salvo

        if (
            self.firing_order == FiringOrder.ALTERNATELY
            or self.firing_order == FiringOrder.UNTIL_MISS
            and salvo.miss
        ):
            self._current_player = next(self._player_cycle)

        return salvo
