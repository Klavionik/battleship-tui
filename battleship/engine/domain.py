import dataclasses
import enum
import itertools
import random
from collections.abc import Awaitable, Callable
from functools import cached_property
from itertools import cycle, pairwise
from typing import Collection, Iterable, Iterator, TypeVar

from pymitter import EventEmitter  # type: ignore[import-untyped]

from battleship.engine import errors, rosters
from battleship.shared.compat import StrEnum

DEFAULT_BOARD_SIZE = 10
ASCII_OFFSET = 64


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    RIGHT = "right"
    LEFT = "left"


class FiringOrder(StrEnum):
    ALTERNATELY = "alternately"
    UNTIL_MISS = "until_miss"


@dataclasses.dataclass
class Ship:
    id: str
    type: str
    hp: int
    cells: list["Coordinate"] = dataclasses.field(default_factory=list, compare=False)

    @property
    def destroyed(self) -> bool:
        return self.hp == 0

    def damage(self) -> None:
        if not self.destroyed:
            self.hp -= 1


@dataclasses.dataclass
class Coordinate:
    x: int
    y: int

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.to_human() == other

        if isinstance(other, Coordinate):
            return (self.x, self.y) == (other.x, other.y)

        raise NotImplementedError(f"Cannot compare Coordinate to {other.__class__.__name__}.")

    def up(self) -> "Coordinate":
        return Coordinate(self.x, self.y - 1)

    def right(self) -> "Coordinate":
        return Coordinate(self.x + 1, self.y)

    def down(self) -> "Coordinate":
        return Coordinate(self.x, self.y + 1)

    def left(self) -> "Coordinate":
        return Coordinate(self.x - 1, self.y)

    @property
    def col(self) -> str:
        return chr(self.x + ASCII_OFFSET + 1)

    @property
    def row(self) -> int:
        return self.y + 1

    @classmethod
    def from_human(cls, coordinate: str) -> "Coordinate":
        col, row = parse_coordinate(coordinate)
        return Coordinate(ord(col) - ASCII_OFFSET - 1, row - 1)

    def to_human(self) -> str:
        return f"{self.col}{self.row}"


@dataclasses.dataclass
class Cell:
    coordinate: Coordinate
    ship: Ship | None = None
    is_shot: bool = False

    def __repr__(self) -> str:
        return f"Cell {self.coordinate.to_human()}"

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
    def col(self) -> str:
        return self.coordinate.col

    @property
    def row(self) -> int:
        return self.coordinate.row


def parse_coordinate(coordinate: str) -> tuple[str, int]:
    try:
        col, row = coordinate[0], int("".join(coordinate[1:]))
    except (IndexError, TypeError, ValueError):
        raise errors.IncorrectCoordinate(f"Cannot parse coordinate {coordinate}.")

    return col, row


def is_valid_position(coordinates: Iterable[Coordinate]) -> None:
    """
    Validates that given coordinates make up either a
    horizontal or a vertical line with no gaps in between.

    Examples:
        A2, A3, A4 is valid. A2, A4, A5 is not.
        B3, C3, D3 is valid. B3, C3, E3 is not.
    """
    sorted_coordinates = sorted(coordinates, key=lambda coord: (coord.x, coord.y))

    for curr, next_ in itertools.pairwise(sorted_coordinates):
        if next_ not in [curr.right(), curr.down()]:
            raise errors.InvalidPosition(f"Position {coordinates} is invalid.")


def position_to_coordinates(position: Collection[str]) -> list[Coordinate]:
    return list(map(Coordinate.from_human, position))


class Board:
    def __init__(self, size: int = DEFAULT_BOARD_SIZE) -> None:
        self.size = size
        self.grid = [
            [Cell(Coordinate(col, row)) for col in range(self.size)] for row in range(self.size)
        ]
        self.ships: list[Ship] = []

    def __repr__(self) -> str:
        return f"<Board {self.size}x{self.size}, {len(self.ships)} ships>"

    @cached_property
    def cells(self) -> list[Cell]:
        return [cell for row in self.grid for cell in row]

    def get_adjacent_cell(self, cell: Cell, direction: Direction) -> Cell | None:
        match direction:
            case Direction.UP:
                coordinate = cell.coordinate.up()
            case Direction.DOWN:
                coordinate = cell.coordinate.down()
            case Direction.RIGHT:
                coordinate = cell.coordinate.right()
            case Direction.LEFT:
                coordinate = cell.coordinate.left()
            case _:
                raise ValueError(f"Invalid direction {direction}.")

        return self.get_cell(coordinate)

    def get_cell(self, coordinate: Coordinate) -> Cell | None:
        if not (0 <= coordinate.x < self.size and 0 <= coordinate.y < self.size):
            return None

        return self.grid[coordinate.y][coordinate.x]

    def has_adjacent_ship(self, coordinate: Coordinate) -> bool:
        cell = self.get_cell(coordinate)

        if not cell:
            raise errors.CellOutOfRange(f"Cell at {coordinate=} does not exist.")

        adjacent_coordinates = [
            cell.coordinate.up(),
            cell.coordinate.right(),
            cell.coordinate.down(),
            cell.coordinate.left(),
        ]
        diagonals = [
            adjacent_coordinates[1].up(),
            adjacent_coordinates[1].down(),
            adjacent_coordinates[3].up(),
            adjacent_coordinates[3].down(),
        ]
        adjacent_coordinates.extend(diagonals)

        cells = [self.get_cell(coor) for coor in adjacent_coordinates]

        return any([cell is not None and cell.ship is not None for cell in cells])

    def place_ship(
        self, coordinates: Collection[Coordinate], ship: Ship, no_adjacent_ships: bool = False
    ) -> None:
        if len(coordinates) != ship.hp:
            raise errors.ShipDoesntFitCells(
                f"Cannot place {ship.hp} HP ship onto {len(coordinates)} cells."
            )

        is_valid_position(coordinates)

        if no_adjacent_ships:
            for coordinate in coordinates:
                if self.has_adjacent_ship(coordinate):
                    raise errors.CannotPlaceShip(f"Coordinate {coordinate} has an adjacent ship.")

        for coordinate in coordinates:
            cell = self.get_cell(coordinate)

            if cell is None:
                raise errors.CellOutOfRange(f"Cell at {coordinate} doesn't exist.")

            cell.set_ship(ship)

        self.ships.append(ship)
        ship.cells.extend(coordinates)

    def hit_cell(self, coordinate: Coordinate) -> Ship | None:
        cell = self.get_cell(coordinate)

        if cell is None:
            raise errors.CellOutOfRange(f"Cell at {coordinate} doesn't exist.")

        cell.hit()
        return cell.ship


@dataclasses.dataclass(unsafe_hash=True)
class Player:
    name: str
    board: Board = dataclasses.field(default_factory=Board, hash=False)

    def __repr__(self) -> str:
        return self.name

    def add_ship(
        self, position: Collection[Coordinate], ship: Ship, no_adjacent_ships: bool = False
    ) -> None:
        self.board.place_ship(position, ship, no_adjacent_ships)

    def attack(self, coordinate: Coordinate) -> Ship | None:
        return self.board.hit_cell(coordinate)

    def count_ships(self, ship_type: rosters.ShipType) -> int:
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
    coordinate: Coordinate
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


class GameEvent:
    pass


@dataclasses.dataclass
class NextMove(GameEvent):
    actor: Player
    subject: Player


@dataclasses.dataclass
class ShipSpawned(GameEvent):
    player: Player
    ship_id: str
    position: Collection[str]
    fleet_ready: bool


@dataclasses.dataclass
class GameEnded(GameEvent):
    winner: Player


@enum.unique
class GameState(StrEnum):
    ARRANGE_FLEET = enum.auto()
    BATTLE = enum.auto()
    END = enum.auto()


Event = TypeVar("Event", bound=GameEvent)
Handler = Callable[[Event], None] | Callable[[Event], Awaitable[None]]


class Game:
    def __init__(
        self,
        player_a: Player,
        player_b: Player,
        roster: rosters.Roster,
        firing_order: FiringOrder = FiringOrder.ALTERNATELY,
        salvo_mode: bool = False,
        no_adjacent_ships: bool = False,
    ) -> None:
        self.player_a = player_a
        self.player_b = player_b
        self.roster = roster
        self.firing_order = firing_order
        self.salvo_mode = salvo_mode
        self.no_adjacent_ships = no_adjacent_ships

        self._player_cycle = pairwise(cycle(random.sample([player_a, player_b], k=2)))
        self._actor, self._subject = next(self._player_cycle)
        self._winner: Player | None = None
        self._can_make_turn = False
        self._state = GameState.ARRANGE_FLEET
        self._ee = EventEmitter()

    def __str__(self) -> str:
        return f"Game <{self.player_a} vs {self.player_b}> <Winner: {self._winner}>"

    @property
    def actor(self) -> Player:
        return self._actor

    @property
    def subject(self) -> Player:
        return self._subject

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def winner(self) -> Player | None:
        return self._winner

    def on(self, event: type[Event], func: Handler[Event]) -> None:
        self._ee.on(event.__name__, func)

    def add_ship(
        self, player: Player, position: Collection[str], roster_id: rosters.ShipId
    ) -> None:
        if self._state != GameState.ARRANGE_FLEET:
            raise RuntimeError(f"Cannot add a new ship, incorrect game state {self._state}.")

        coordinates = [Coordinate.from_human(point) for point in position]

        if player.get_ship(roster_id) is None:
            ship = self._build_ship(roster_id)
            player.add_ship(coordinates, ship, self.no_adjacent_ships)
        else:
            raise errors.ShipLimitExceeded(
                f"Player {player.name} already has a ship with roster id {roster_id}."
            )

        self._emit(
            ShipSpawned(
                player=player,
                fleet_ready=self._is_fleet_ready(player),
                ship_id=roster_id,
                position=position,
            )
        )
        self._check_game_ready()

    def fire(self, position: Collection[str]) -> Salvo:
        if self._state == GameState.ARRANGE_FLEET:
            raise errors.GameNotReady("Place all ships before firing.")

        if self._state == GameState.END:
            raise errors.GameEnded(f"{self.winner} won this game.")

        if len(position) > 1 and not self.salvo_mode:
            raise errors.TooManyShots("Multiple shots in one turn permitted only in salvo mode.")

        assert self._actor, "No actor"

        if self.salvo_mode and (len(position) != self._actor.ships_alive):
            raise errors.IncorrectShots(
                f"Number of shots {len(position)} must be equal "
                f"to the number of alive ships {self._actor.ships_alive}."
            )

        salvo = Salvo(actor=self.actor, subject=self.subject)

        for point in position:
            coordinate = Coordinate.from_human(point)
            maybe_ship = self.subject.attack(coordinate)
            shot = Shot(
                coordinate=coordinate,
                hit=maybe_ship is not None,
                ship=maybe_ship,
            )
            salvo.add_shot(shot)

        self._can_make_turn = True
        return salvo

    def turn(self, salvo: Salvo) -> None:
        if not self._can_make_turn:
            raise RuntimeError("Cannot make turn at this time. Try calling fire() before.")

        self._can_make_turn = False

        if salvo.subject.ships_alive == 0:
            self._winner = salvo.actor
            self._state = GameState.END
            self._emit(GameEnded(winner=salvo.actor))
            self._ee.off_all()
        else:
            if (
                self.firing_order == FiringOrder.ALTERNATELY
                or self.firing_order == FiringOrder.UNTIL_MISS
                and salvo.miss
            ):
                self._cycle_players()

            self._emit(NextMove(actor=self._actor, subject=self._subject))

    def _is_fleet_ready(self, player: Player) -> bool:
        return {ship.id for ship in player.ships} == {item.id for item in self.roster}

    def _build_ship(self, ship_id: rosters.ShipId) -> Ship:
        try:
            item = self.roster[ship_id]
            return Ship(*item)
        except KeyError:
            raise errors.ShipNotFound(f"No ship with ID {ship_id} in the roster.")

    def _check_game_ready(self) -> None:
        if self._is_fleet_ready(self.player_a) and self._is_fleet_ready(self.player_b):
            self._state = GameState.BATTLE
            self._emit(NextMove(self._actor, self._subject))

    def _cycle_players(self) -> None:
        self._actor, self._subject = next(self._player_cycle)

    def _emit(self, event: GameEvent) -> None:
        self._ee.emit_future(event.__class__.__name__, event)
