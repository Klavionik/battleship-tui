import dataclasses
import string
from itertools import cycle
from typing import Iterator

from battleship import errors


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


@dataclasses.dataclass
class Cell:
    col: str
    row: int
    ship: Ship | None = None
    is_shot: bool = False

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


class Grid:
    def __init__(self, cols: int = 10, rows: int = 10):
        self._cols = cols
        self._rows = rows
        self._letters = string.ascii_uppercase[:cols]
        self._numbers = tuple(range(1, rows + 1))
        self._cells = [[Cell(col, row) for col in self._letters] for row in self._numbers]

    def __getitem__(self, coordinate: str) -> Cell:
        col, row = self._parse_coordinate(coordinate)
        return self._cells[row][col]

    def __str__(self) -> str:
        return f"Grid {self._cols}x{self._rows}"

    def _parse_coordinate(self, coordinate: str) -> tuple[int, int]:
        """
        Coordinate is a string where the zero element is
        a letter in range of the board size and the other elements
        are integers that make up a number in range of the board size.

        :param coordinate: Cell coordinate (like A1, B12, H4 etc.).
        :return: Cell cols index and cell row index.
        """
        try:
            col, row = coordinate[0], int("".join(coordinate[1:]))
        except (IndexError, TypeError, ValueError):
            raise errors.IncorrectCoordinate(f"Cannot parse coordinate {coordinate}.")

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
        # TODO: Check that cells make up a vertical or a horizontal line.
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

    def __str__(self) -> str:
        return self.name

    @property
    def ships_left(self) -> int:
        return len([ship for ship in self.board.ships if ship.hp > 0])

    def place_ship(self, *coordinates: str, ship: Ship) -> None:
        self.board.place_ship(*coordinates, ship=ship)


class Turn:
    def __init__(self, player: Player, hostile: Player) -> None:
        self.player = player
        self.hostile = hostile

    def __str__(self) -> str:
        return f"Turn <{self.player} vs. {self.hostile}>"

    def strike(self, target: str) -> Ship | None:
        return self.hostile.board.hit_cell(target)


class Game:
    def __init__(self, player_a: Player, player_b: Player) -> None:
        self.player_a = player_a
        self.player_b = player_b
        self.players: Iterator[tuple[Player, Player]] = cycle(
            zip([self.player_a, self.player_b], [self.player_b, self.player_a])
        )
        self.players_map: dict[str, Player] = {
            player_a.name: player_a,
            player_b.name: player_b,
        }
        self.winner: Player | None = None

    def __iter__(self) -> Iterator[Turn]:
        for player, hostile in self.players:
            yield Turn(player, hostile)

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

    def place_ship(self, *coordinates: str, player: str, ship: Ship) -> None:
        self.get_player(player).place_ship(*coordinates, ship=ship)
