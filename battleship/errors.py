class BattleshipError(Exception):
    pass


class IncorrectCoordinate(BattleshipError):
    pass


class CellOutOfRange(BattleshipError):
    pass


class CellTaken(BattleshipError):
    pass


class CellAlreadyShot(BattleshipError):
    pass


class PlayerNotFound(BattleshipError):
    pass


class TurnUnused(BattleshipError):
    pass


class ShipsNotPlaced(BattleshipError):
    pass
