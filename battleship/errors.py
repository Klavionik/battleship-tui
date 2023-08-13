class BattleshipError(Exception):
    pass


class CellNotFound(BattleshipError):
    pass


class CellTaken(BattleshipError):
    pass


class CellAlreadyShot(BattleshipError):
    pass
