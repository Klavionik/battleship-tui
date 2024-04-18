import random
from collections import deque
from typing import Iterable

from battleship.engine import domain, errors, rosters


class TargetCaller:
    def __init__(self, board: domain.Board) -> None:
        self.board = board
        self.next_targets: deque[domain.Cell] = deque()

    def call_out(self, *, count: int = 1) -> list[str]:
        cells = self._get_targets(count)
        return [cell.coordinate for cell in cells]

    def provide_feedback(self, shots: Iterable[domain.Shot]) -> None:
        for shot in shots:
            if shot.hit and not shot.ship.destroyed:  # type: ignore
                neighbors = self._find_neighbor_cells(self.board.get_cell(shot.coordinate))
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
        candidates = [cell for cell in self.board.cells if not cell.is_shot]
        return random.sample(candidates, k=min(len(candidates), count))

    def _find_neighbor_cells(self, cell: domain.Cell) -> list[domain.Cell]:
        cells = []

        for direction in list(domain.Direction):
            candidate = self.board.get_adjacent_cell(cell, direction)
            if candidate is None or candidate.is_shot or candidate in self.next_targets:
                continue

            cells.append(candidate)

        return cells


class Autoplacer:
    def __init__(self, board: domain.Board, ship_suite: rosters.Roster):
        self.board = board
        self.ship_hp_map: dict[rosters.ShipType, rosters.ShipHitpoints] = dict(
            (item.type, item.hp) for item in ship_suite
        )

    def place(self, ship_type: rosters.ShipType) -> list[str]:
        ship_hp = self.ship_hp_map[ship_type]
        position: list[str] = []
        empty_cells = [cell for cell in self.board.cells if cell.ship is None]
        directions = list[domain.Direction](domain.Direction)
        random.shuffle(empty_cells)
        random.shuffle(directions)

        for cell in empty_cells:  # Get next random cell.
            for direction in directions:  # Get next random direction.
                start_cell = cell  # For every direction, build from this random cell.
                # Try to found enough empty cells to place the ship in this direction.
                for _ in range(ship_hp):
                    # Get the next cell in this direction.
                    next_cell = self.board.get_adjacent_cell(start_cell, direction)

                    # If there is no cell or the cell is taken,
                    # clear the progress and try another direction.
                    if next_cell is None or next_cell.ship is not None:
                        position.clear()
                        break

                    # Otherwise, save the coordinate.
                    position.append(next_cell.coordinate)

                    # If there is enough cells to place the ship, return the position.
                    if len(position) == ship_hp:
                        return position

                    # Otherwise, move forward in this direction.
                    start_cell = next_cell

        raise errors.CannotPlaceShip(f"Cannot find suitable position for {ship_type}.")
