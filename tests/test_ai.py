import random

import pytest

from battleship.engine import ai, domain, errors, roster


def test_target_caller_calls_correct_amount_of_targets():
    board = domain.Board()
    target_caller = ai.TargetCaller(board)

    assert len(target_caller.call_out()) == 1
    assert len(target_caller.call_out(count=5)) == 5


def test_target_caller_doesnt_target_shot_cells():
    random.seed(42)
    board = domain.Board(size=2)
    caller = ai.TargetCaller(board)

    board.grid[0][0].hit()
    board.grid[0][1].hit()

    # Request 4 targets, but only 2 cells are not shot yet.
    targets = caller.call_out(count=4)

    assert targets == [board.grid[1][0].coordinate, board.grid[1][1].coordinate]


def test_target_caller_targets_adjacent_cells_after_hit_until_all_tried():
    random.seed(42)
    board = domain.Board()
    ship = domain.Ship("id", "ship", 4)
    board.place_ship(["B2", "B3", "B4", "B5"], ship)
    board.hit_cell("B3")
    shot = domain.Shot("B3", hit=True, ship=ship)
    caller = ai.TargetCaller(board)

    caller.provide_feedback([shot])  # Adds 4 adjacent cells to next targets.

    assert [t.coordinate for t in caller.next_targets] == ["B2", "B4", "C3", "A3"]
    assert caller.call_out() == ["B2"]
    assert [t.coordinate for t in caller.next_targets] == ["B4", "C3", "A3"]
    # When all next targets are called out, caller starts mixing in random cells.
    assert caller.call_out(count=4) == ["B4", "C3", "A3", "C9"]


@pytest.mark.parametrize("ship", [*roster.get_roster("classic")])
def test_autoplacer_position_matches_ship_hp(ship):
    board = domain.Board()
    autoplacer = ai.Autoplacer(board, roster.get_roster("classic"))

    position = autoplacer.place(ship_type=ship.type)

    assert len(position) == ship.hp


@pytest.mark.parametrize("ship", [*roster.get_roster("classic")])
def test_autoplacer_position_is_valid(ship):
    board = domain.Board()
    autoplacer = ai.Autoplacer(board, roster.get_roster("classic"))

    position = autoplacer.place(ship_type=ship.type)

    assert domain.is_valid_position(position) is None


def test_autoplacer_raises_error_if_no_place_for_ship():
    board = domain.Board(size=4)
    autoplacer = ai.Autoplacer(board, roster.get_roster("classic"))

    with pytest.raises(errors.CannotPlaceShip):
        autoplacer.place("carrier")
