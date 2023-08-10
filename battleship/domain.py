import dataclasses


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
    row: int
    column: str
    ship: Ship = None
    is_shot: bool = False

    def hit(self):
        self.is_shot = True

        if self.ship is not None:
            self.ship.hit()
