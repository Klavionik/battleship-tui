import random
from collections import deque
from typing import Iterable

from battleship.engine import domain


class TargetCaller:
    def __init__(self, enemy: domain.Board) -> None:
        self.enemy = enemy
        self.next_targets: deque[domain.Cell] = deque()

    def call_out(self, *, count: int = 1) -> list[str]:
        cells = self._get_targets(count)
        return [cell.coordinate for cell in cells]

    def provide_feedback(self, outcome: Iterable[domain.FireAttempt]) -> None:
        for attempt in outcome:
            if attempt.hit and not attempt.ship.destroyed:  # type: ignore
                neighbors = self._find_neighbor_cells(self.enemy.get_cell(attempt.coordinate))
                self.next_targets.extend(neighbors)

    def _get_targets(self, count: int) -> list[domain.Cell]:
        targets: list[domain.Cell] = []

        while len(self.next_targets) and len(targets) != count:
            next_target = self.next_targets.popleft()
            targets.append(next_target)

        if len(targets) != count:
            random_targets = self._find_random_targets(count - len(targets))
            targets.extend(random_targets)

        return targets

    def _find_random_targets(self, count: int) -> list[domain.Cell]:
        candidates = [cell for cell in self.enemy.cells if not cell.is_shot]
        return random.sample(candidates, k=min(len(candidates), count))

    def _find_neighbor_cells(self, cell: domain.Cell) -> list[domain.Cell]:
        cells = []

        for direction in list(domain.Direction):
            candidate = self.enemy.get_adjacent_cell(cell, direction)  # type: ignore[arg-type]
            if candidate is None or candidate.is_shot or candidate in self.next_targets:
                continue

            cells.append(candidate)

        return cells


class Autoplacer:
    def __init__(self, board: domain.Board, ship_suite: Iterable[domain.ShipConfig]):
        self.board = board
        self.ship_hp_map = dict(ship_suite)

    def place(self, ship_type: domain.ShipType) -> list[str]:
        ship_hp = self.ship_hp_map[ship_type]
        position: list[str] = []
        empty_cells = [cell for cell in self.board.cells if cell.ship is None]

        while len(position) != ship_hp:
            direction: domain.Direction = random.choice(list(domain.Direction))  # type: ignore
            start_cell = random.choice(empty_cells)

            for _ in range(ship_hp):
                next_cell = self.board.get_adjacent_cell(start_cell, direction)

                if next_cell is None or next_cell.ship is not None:
                    position.clear()
                    break

                position.append(next_cell.coordinate)
                start_cell = next_cell

        return position
