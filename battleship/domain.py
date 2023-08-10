class Ship:
    kind: str
    hitpoints: int

    @property
    def dead(self):
        return self.hitpoints == 0

    def hit(self):
        if not self.dead:
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
