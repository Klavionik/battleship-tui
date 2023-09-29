import random
from abc import ABC, abstractmethod
from typing import Collection

from battleship.engine import domain


class Algorithm(ABC):
    @abstractmethod
    def find_next_targets(self, board: domain.Board, count: int) -> list[domain.Cell]:
        ...


class RandomAlgorithm(Algorithm):
    def find_next_targets(self, board: domain.Board, count: int) -> list[domain.Cell]:
        candidates: list[domain.Cell] = []

        for row in board.grid:
            for cell in row:
                if cell.is_shot:
                    continue

                candidates.append(cell)

        return random.sample(candidates, k=min(len(candidates), count))


class TargetCaller:
    def __init__(self, enemy_board: domain.Board, algorithm: Algorithm | None = None):
        self.enemy = enemy_board
        self.algorithm = algorithm or RandomAlgorithm()

    def call_out(self, *, count: int = 1) -> Collection[str]:
        cells = self.algorithm.find_next_targets(self.enemy, count)
        return [cell.coordinate for cell in cells]
