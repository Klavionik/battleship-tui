class Ship:
    kind: str
    hitpoints: int

    @property
    def dead(self):
        return self.hitpoints == 0

    def hit(self):
        if not self.dead:
            self.hitpoints -= 1


class Battleship(Ship):
    kind = "battleship"
    hitpoints = 4
