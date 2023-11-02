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


class ShipsNotPlaced(BattleshipError):
    pass


class ShipDoesntFitCells(BattleshipError):
    pass


class ShipNotFound(BattleshipError):
    pass


class ShipLimitExceeded(BattleshipError):
    pass


class InvalidPosition(BattleshipError):
    pass


class GameNotReady(BattleshipError):
    pass


class GameEnded(BattleshipError):
    pass


class TooManyShots(BattleshipError):
    pass


class IncorrectShots(BattleshipError):
    pass


class CannotPlaceShip(BattleshipError):
    pass
