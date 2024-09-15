import itertools
import random

import pytest

from battleship.engine import ai, domain, errors, rosters


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

    assert targets == [
        board.grid[1][0].coordinate.to_human(),
        board.grid[1][1].coordinate.to_human(),
    ]


def test_target_caller_targets_adjacent_cells_after_hit_until_all_tried():
    random.seed(42)
    board = domain.Board()
    ship = domain.Ship("id", "ship", 4)
    board.place_ship(domain.position_to_coordinates(["B2", "B3", "B4", "B5"]), ship)
    board.hit_cell(domain.Coordinate.from_human("B3"))
    shot = domain.Shot(domain.Coordinate.from_human("B3"), hit=True, ship=ship)
    caller = ai.TargetCaller(board)

    caller.provide_feedback([shot])  # Adds 4 adjacent cells to next targets.

    assert [t.coordinate.to_human() for t in caller.next_targets] == ["B2", "B4", "C3", "A3"]
    assert caller.call_out() == ["B2"]
    assert [t.coordinate.to_human() for t in caller.next_targets] == ["B4", "C3", "A3"]
    # When all next targets are called out, caller starts mixing in random cells.
    assert caller.call_out(count=4) == ["B4", "C3", "A3", "C9"]


@pytest.mark.parametrize(
    "ship_position, excluded_cells",
    [
        ["B1", ["A2", "C2", "A1", "B2", "C1"]],  # Ship positioned at the top edge.
        ["B2", ["A2", "B3", "C2", "A1", "C1", "A3", "C3", "B1"]],
    ],
)
def test_target_caller_excludes_adjacent_cells_if_adjacent_ships_disallowed(
    ship_position, excluded_cells
):
    board = domain.Board()
    ship = domain.Ship("id", "ship", 1)
    board.place_ship(domain.position_to_coordinates([ship_position]), ship)
    board.hit_cell(domain.Coordinate.from_human(ship_position))
    shot = domain.Shot(domain.Coordinate.from_human(ship_position), hit=True, ship=ship)
    caller = ai.TargetCaller(board, no_adjacent_ships=True)

    caller.provide_feedback([shot])

    assert [c.to_human() for c in caller.excluded_cells] == excluded_cells


def test_target_caller_clears_next_targets_if_ship_destroyed_and_adjacent_ships_disallowed():
    board = domain.Board()
    caller = ai.TargetCaller(board, no_adjacent_ships=True)
    ship = domain.Ship("id", "ship", 2)
    board.place_ship(domain.position_to_coordinates(["B2", "B3"]), ship)

    board.hit_cell(domain.Coordinate.from_human("B2"))
    shot = domain.Shot(domain.Coordinate.from_human("B2"), hit=True, ship=ship)
    caller.provide_feedback([shot])

    assert len(caller.next_targets) == 4

    board.hit_cell(domain.Coordinate.from_human("B3"))
    next_shot = domain.Shot(domain.Coordinate.from_human("B3"), hit=True, ship=ship)
    caller.provide_feedback([next_shot])

    assert not len(caller.next_targets)


@pytest.mark.parametrize("ship", [*rosters.get_roster("classic")])
def test_autoplacer_position_matches_ship_hp(ship):
    board = domain.Board()
    autoplacer = ai.Autoplacer(board, rosters.get_roster("classic"), no_adjacent_ships=False)

    position = autoplacer.place(ship_type=ship.type)

    assert len(position) == ship.hp


@pytest.mark.parametrize("ship", [*rosters.get_roster("classic")])
def test_autoplacer_position_is_valid(ship):
    board = domain.Board()
    autoplacer = ai.Autoplacer(board, rosters.get_roster("classic"), no_adjacent_ships=False)

    position = autoplacer.place(ship_type=ship.type)

    assert domain.is_valid_position(position) is None


@pytest.mark.parametrize(
    "roster,adjacent_ships", [*itertools.product(rosters.get_rosters().values(), (True, False))]
)
def test_autoplacer_can_place_the_whole_fleet(roster, adjacent_ships):
    board = domain.Board()
    autoplacer = ai.Autoplacer(board, roster, no_adjacent_ships=adjacent_ships)

    for item in roster:
        autoplacer.place(ship_type=item.type)

    assert True


def test_autoplacer_raises_error_if_no_place_for_ship():
    board = domain.Board(size=4)
    autoplacer = ai.Autoplacer(board, rosters.get_roster("classic"), no_adjacent_ships=False)

    with pytest.raises(errors.CannotPlaceShip):
        autoplacer.place("carrier")


def test_autoplacer_respects_no_ships_touch_rule():
    board = domain.Board(size=3)
    ship = domain.Ship(id="1", hp=3, type="ship")
    roster = rosters.Roster(name="test", items=[rosters.RosterItem(id="1", type="ship", hp=3)])
    # Place the ship in the center of the 3x3 board.
    board.place_ship(domain.position_to_coordinates(["B1", "B2", "B3"]), ship)
    autoplacer = ai.Autoplacer(board, roster, no_adjacent_ships=True)

    # Autoplacer can't place another ship on the board without violating the rule.
    with pytest.raises(errors.CannotPlaceShip):
        autoplacer.place(ship_type="ship")
