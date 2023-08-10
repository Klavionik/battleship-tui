import dataclasses
import string


class Ship:
    kind: str
    hitpoints: int

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


@dataclasses.dataclass
class Cell:
    COLUMNS = tuple(string.ascii_uppercase[:10])
    ROWS = tuple(range(1, 11))

    row: int
    column: str
    ship: Ship = None
    is_shot: bool = False

    def hit(self):
        self.is_shot = True

        if self.ship is not None:
            self.ship.hit()


class Board:
    def __init__(self):
        self.cells = [[Cell(row, column) for column in Cell.COLUMNS] for row in Cell.ROWS]
