import random

import pytest

from battleship.engine import ai, domain


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


@pytest.mark.parametrize("ship", [*domain.CLASSIC_SHIP_SUITE])
def test_autoplacer_position_matches_ship_hp(ship):
    type_, hp = ship
    board = domain.Board()
    autoplacer = ai.Autoplacer(board, domain.CLASSIC_SHIP_SUITE)

    position = autoplacer.place(ship_type=type_)

    assert len(position) == hp


@pytest.mark.parametrize("ship", [*domain.CLASSIC_SHIP_SUITE])
def test_autoplacer_position_is_valid(ship):
    type_, hp = ship
    board = domain.Board()
    autoplacer = ai.Autoplacer(board, domain.CLASSIC_SHIP_SUITE)

    position = autoplacer.place(ship_type=type_)

    assert domain.is_valid_position(position) is None
