import random
from collections import deque
from typing import Iterable

from battleship.engine import domain, errors, rosters


class TargetCaller:
    def __init__(self, board: domain.Board, no_adjacent_ships: bool = False) -> None:
        self.board = board
        self.no_adjacent_ships = no_adjacent_ships
        self.next_targets: deque[domain.Coordinate] = deque()
        self.excluded_cells: set[domain.Coordinate] = set()

    def call_out(self, *, count: int = 1) -> list[str]:
        targets = self._get_targets(count)
        return [target.to_human() for target in targets]

    def provide_feedback(self, shots: Iterable[domain.Shot]) -> None:
        for shot in shots:
            if shot.hit:
                assert shot.ship, "Shot was a hit, but no ship present"

                if shot.ship.destroyed and self.no_adjacent_ships:
                    coordinates = self._find_cells_around_ship(shot.ship)
                    self.excluded_cells.update(coordinates)
                    self.next_targets.clear()
                elif not shot.ship.destroyed:
                    cells = self._find_adjacent_cells(shot.coordinate)
                    self.next_targets.extend(cells)

    def _get_targets(self, count: int) -> list[domain.Coordinate]:
        targets: list[domain.Coordinate] = []

        while len(self.next_targets) and len(targets) != count:
            next_target = self.next_targets.popleft()
            targets.append(next_target)

        if len(targets) != count:
            random_targets = self._find_random_targets(count - len(targets))
            targets.extend(random_targets)

        return targets

    def _find_random_targets(self, count: int) -> list[domain.Coordinate]:
        candidates = [
            cell.coordinate
            for cell in self.board.cells
            if not (cell.is_shot or cell.coordinate in self.excluded_cells)
        ]
        return random.sample(candidates, k=min(len(candidates), count))

    def _find_adjacent_cells(self, coordinate: domain.Coordinate) -> list[domain.Coordinate]:
        cells = []

        for cell_ in self.board.get_adjacent_cells(coordinate, with_diagonals=False):
            if (
                cell_.is_shot
                or cell_.coordinate in self.next_targets
                or cell_.coordinate in self.excluded_cells
            ):
                continue

            cells.append(cell_.coordinate)

        return cells

    def _find_cells_around_ship(self, ship: domain.Ship) -> list[domain.Coordinate]:
        cells = []

        for coordinate in ship.cells:
            adjacent_cells = self.board.get_adjacent_cells(coordinate)
            adjacent_coordinates = [
                cell.coordinate
                for cell in adjacent_cells
                if not cell.is_shot and cell.coordinate not in ship.cells
            ]

            cells.extend(adjacent_coordinates)

        return cells


class Autoplacer:
    def __init__(self, board: domain.Board, ship_suite: rosters.Roster, no_adjacent_ships: bool):
        self.board = board
        self.ship_hp_map: dict[rosters.ShipType, rosters.ShipHitpoints] = dict(
            (item.type, item.hp) for item in ship_suite
        )
        self.no_adjacent_ships = no_adjacent_ships

    def place(self, ship_type: rosters.ShipType) -> list[domain.Coordinate]:
        ship_hp = self.ship_hp_map[ship_type]
        position: list[domain.Coordinate] = []
        empty_cells = [
            cell.coordinate
            for cell in self.board.cells
            if not self.board.has_ship_at(cell.coordinate)
        ]
        directions = list[domain.Direction](domain.Direction)
        random.shuffle(empty_cells)
        random.shuffle(directions)

        for cell in empty_cells:  # Get next random cell.
            for direction in directions:  # Get next random direction.
                start_cell = cell  # For every direction, build from this random cell.

                # Try to found enough empty cells to place the ship in this direction.
                for _ in range(ship_hp):
                    # Get the next cell in this direction.
                    next_cell = start_cell.next(direction)

                    # If there is no cell or the cell is taken,
                    # clear the progress and try another direction.
                    if not self.board.has_cell(next_cell) or self.board.has_ship_at(next_cell):
                        position.clear()
                        break

                    # Otherwise, save the coordinate.
                    position.append(next_cell)

                    # If there is enough cells to place the ship, return the position.
                    if len(position) == ship_hp:
                        # If there's a flag set, check for adjacent ships.
                        if self.no_adjacent_ships and any(
                            self.board.has_adjacent_ship(c) for c in position
                        ):
                            continue

                        return position

                    # Otherwise, move forward in this direction.
                    start_cell = next_cell

        raise errors.CannotPlaceShip(f"Cannot find suitable position for {ship_type}.")
