import dataclasses
import string
from itertools import cycle


class Ship:
    kind: str
    hitpoints: int

    def __str__(self):
        return self.kind

    @property
    def is_dead(self):
        return self.hitpoints == 0

    def hit(self):
        if not self.is_dead:
            self.hitpoints -= 1


class Carrier(Ship):
    kind = "carrier"
    hitpoints = 5


class Battleship(Ship):
    kind = "battleship"
    hitpoints = 4


class Cruiser(Ship):
    kind = "cruiser"
    hitpoints = 3


class Submarine(Ship):
    kind = "submarine"
    hitpoints = 3


class Destroyer(Ship):
    kind = "destroyer"
    hitpoints = 2


class CellTaken(RuntimeError):
    pass


class CellAlreadyShot(RuntimeError):
    pass


@dataclasses.dataclass
class Cell:
    COLUMNS = tuple(string.ascii_uppercase[:10])
    ROWS = tuple(range(1, 11))

    row: int
    column: str
    ship: Ship = None
    is_shot: bool = False

    def hit(self):
        if self.is_shot:
            raise CellAlreadyShot(f"You can't shot the same cell {self} twice.")

        self.is_shot = True

        if self.ship is not None:
            self.ship.hit()

    def place_ship(self, ship: Ship):
        if self.ship is not None:
            raise CellTaken(f"Cell {self} already has a ship.")

        self.ship = ship

    def __str__(self):
        return f"{self.column}{self.row}"


class CellNotFound(ValueError):
    pass


class Board:
    def __init__(self):
        self.cells = [[Cell(row, column) for column in Cell.COLUMNS] for row in Cell.ROWS]

    def place_ship(self, *cells: str, ship: Ship):
        for cell_name in cells:
            cell = self.find_cell(cell_name)
            cell.place_ship(ship)

    def find_cell(self, cell_name: str):
        col, row = cell_name[0], int("".join(cell_name[1:]))

        try:
            col_index = Cell.COLUMNS.index(col)
        except ValueError:
            raise CellNotFound(f"Incorrect column {col}.")

        try:
            row_index = Cell.ROWS.index(row)
        except ValueError:
            raise CellNotFound(f"Incorrect row {row}.")

        return self.cells[row_index][col_index]

    def shoot(self, target: str) -> Cell:
        cell = self.find_cell(target)
        cell.hit()
        return cell


class Player:
    def __init__(self, name: str, board: Board):
        self.name = name
        self.board = board
        self.ships = []

    def place_ship(self, *cells: str, ship: Ship):
        self.board.place_ship(*cells, ship=ship)
        self.ships.append(ship)

    def __str__(self):
        return self.name

    @property
    def ships_left(self):
        return len([ship for ship in self.ships if ship.hitpoints > 0])


class Turn:
    def __init__(self, player: Player, hostile: Player):
        self.player = player
        self.hostile = hostile

    def fire(self, target: str) -> Cell:
        return self.hostile.board.shoot(target)


class Game:
    def __init__(self, player_a: Player, player_b: Player):
        self.player_a = player_a
        self.player_b = player_b
        self.players = cycle(zip([self.player_a, self.player_b], [self.player_b, self.player_a]))
        self.winner = None

    def __iter__(self):
        for player, hostile in self.players:
            yield Turn(player, hostile)

            if hostile.ships_left == 0:
                self.winner = player
                break
