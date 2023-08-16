import dataclasses
import itertools
import string
from itertools import cycle
from typing import Callable, Iterable, Iterator, TypeAlias

from battleship import errors

Kind: TypeAlias = str
Hitpoints: TypeAlias = int
ShipConfig: TypeAlias = tuple[Kind, Hitpoints]
SpawnCallback: TypeAlias = Callable[[Iterable[str]], None]

CLASSIC_SHIP_SUITE = [
    ("carrier", 5),
    ("battleship", 4),
    ("cruiser", 3),
    ("submarine", 3),
    ("destroyer", 2),
]


@dataclasses.dataclass
class Ship:
    kind: str
    hp: int

    def __str__(self) -> str:
        return self.kind

    @property
    def destroyed(self) -> bool:
        return self.hp == 0

    def damage(self) -> None:
        if not self.destroyed:
            self.hp -= 1


class Cell:
    def __init__(self, col: str, row: int):
        self.col = col
        self.row = row
        self.ship: Ship | None = None
        self.is_shot = False

    def __str__(self) -> str:
        return self.coordinate

    def hit(self) -> None:
        if self.is_shot:
            raise errors.CellAlreadyShot(f"You can't shot the same cell {self} twice.")

        self.is_shot = True

        if self.ship is not None:
            self.ship.damage()

    def assign_ship(self, ship: Ship) -> None:
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


class Grid:
    def __init__(self, cols: int = 10, rows: int = 10):
        self._cols = cols
        self._rows = rows
        self._letters = string.ascii_uppercase[:cols]
        self._numbers = tuple(range(1, rows + 1))
        self._cells = [[Cell(col, row) for col in self._letters] for row in self._numbers]

    def __getitem__(self, coordinate: str) -> Cell:
        col, row = self._check_coordinate(coordinate)
        return self._cells[row][col]

    def __str__(self) -> str:
        return f"Grid {self._cols}x{self._rows}"

    def _check_coordinate(self, coordinate: str) -> tuple[int, int]:
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


class Board:
    def __init__(self, cols: int = 10, rows: int = 10) -> None:
        self.grid = Grid(cols, rows)
        self.ships: list[Ship] = []

    def __str__(self) -> str:
        return f"Board, {len(self.ships)} ships left"

    def __contains__(self, item: Ship) -> bool:
        if not isinstance(item, Ship):
            raise TypeError(f"Cannot test if board contains {type(item)}.")

        return item in self.ships

    def place_ship(self, *cells: str, ship: Ship) -> None:
        if len(cells) != ship.hp:
            raise errors.ShipDoesntFitCells(
                f"Cannot place {ship.hp} HP ship onto {len(cells)} cells."
            )

        is_valid_position(cells)

        for coordinate in cells:
            cell = self.grid[coordinate]
            cell.assign_ship(ship)

        self.ships.append(ship)

    def hit_cell(self, target: str) -> Ship | None:
        cell: Cell = self.grid[target]
        cell.hit()
        return cell.ship


class Player:
    def __init__(self, name: str, board: Board) -> None:
        self.name = name
        self.board = board
        self.ready = False

    def __str__(self) -> str:
        return self.name

    @property
    def ships_left(self) -> int:
        return len([ship for ship in self.board.ships if ship.hp > 0])


class Turn:
    def __init__(self, player: Player, hostile: Player) -> None:
        self.player = player
        self.hostile = hostile
        self.called = False

    def __str__(self) -> str:
        return f"Turn <{self.player} vs. {self.hostile}>"

    def strike(self, target: str) -> Ship | None:
        self.called = True
        return self.hostile.board.hit_cell(target)


class Game:
    def __init__(
        self, player_a: Player, player_b: Player, ship_suite: Iterable[ShipConfig]
    ) -> None:
        self.player_a = player_a
        self.player_b = player_b
        self.ship_suite = ship_suite
        self.players: Iterator[tuple[Player, Player]] = cycle(
            zip([self.player_a, self.player_b], [self.player_b, self.player_a])
        )
        self.players_map: dict[str, Player] = {
            player_a.name: player_a,
            player_b.name: player_b,
        }
        self.winner: Player | None = None

    def __iter__(self) -> Iterator[Turn]:
        if not (self.player_a.ready and self.player_b.ready):
            raise errors.ShipsNotPlaced("Players should place ships before starting the game.")

        for player, hostile in self.players:
            next_turn = Turn(player, hostile)
            yield next_turn

            if not next_turn.called:
                raise errors.TurnUnused("strike() was not called on Turn.")

            if hostile.ships_left == 0:
                self.winner = player
                break

    def __str__(self) -> str:
        return f"Game <{self.player_a} vs {self.player_b}> <Winner: {self.winner}>"

    def get_player(self, name: str) -> Player:
        try:
            return self.players_map[name]
        except KeyError:
            raise errors.PlayerNotFound(f"Player {name} is not in this game.")

    def spawn_ships(self, player: str) -> Iterator[tuple[Ship, SpawnCallback]]:
        player_ = self.get_player(player)

        for kind, hp in self.ship_suite:
            ship = Ship(kind, hp)
            ship_spawned = False

            def spawn_callback(position: Iterable[str]) -> None:
                nonlocal ship_spawned
                player_.board.place_ship(*position, ship=ship)  # noqa: B023
                ship_spawned = True

            yield ship, spawn_callback

            if not ship_spawned:
                raise RuntimeError(f"You forgot to call spawn callback to spawn {ship}.")

        player_.ready = True
