import enum
import random
from abc import ABC, abstractmethod
from typing import Iterable

from battleship.engine import domain, errors


class ShipDirection(enum.StrEnum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class Algorithm(ABC):
    @abstractmethod
    def find_next_targets(self, board: domain.Board, count: int) -> list[domain.Cell]:
        ...


class RandomAlgorithm(Algorithm):
    def find_next_targets(self, board: domain.Board, count: int) -> list[domain.Cell]:
        candidates = [cell for cell in board.cells if not cell.is_shot]
        return random.sample(candidates, k=min(len(candidates), count))


class TargetCaller:
    def __init__(self, enemy_board: domain.Board, algorithm: Algorithm | None = None):
        self.enemy = enemy_board
        self.algorithm = algorithm or RandomAlgorithm()

    def call_out(self, *, count: int = 1) -> list[str]:
        cells = self.algorithm.find_next_targets(self.enemy, count)
        return [cell.coordinate for cell in cells]


class Autoplacer:
    def __init__(self, board: domain.Board, ship_suite: Iterable[domain.ShipConfig]):
        self.board = board
        self.ship_hp_map = dict(ship_suite)

    def place(self, ship_type: domain.ShipType) -> list[str]:
        ship_hp = self.ship_hp_map[ship_type]
        position: list[str] = []
        empty_cells = [cell for cell in self.board.cells if cell.ship is None]

        while len(position) != ship_hp:
            direction = random.choice(list(ShipDirection))
            next_cell: domain.Cell = random.choice(empty_cells)

            for _ in range(ship_hp):
                match direction:
                    case ShipDirection.UP:
                        coord = next_cell.upper_coordinate
                    case ShipDirection.DOWN:
                        coord = next_cell.lower_coordinate
                    case ShipDirection.LEFT:
                        coord = next_cell.left_coordinate
                    case _:
                        coord = next_cell.right_coordinate

                try:
                    next_cell = self.board.get_cell(coord)
                except errors.CellOutOfRange:
                    position.clear()
                    break

                if next_cell.ship is not None:
                    position.clear()
                    break

                position.append(next_cell.coordinate)

        return position
