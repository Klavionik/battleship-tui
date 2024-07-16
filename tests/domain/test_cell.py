import pytest

from battleship.engine import domain, errors


def test_cell_can_be_assigned_ship():
    ship = domain.Ship(id="id", type="ship", hp=1)
    cell = domain.Cell(domain.Coordinate(0, 0))

    cell.set_ship(ship)

    assert cell.ship is ship


def test_cell_hits_bound_ship():
    ship = domain.Ship(id="id", type="ship", hp=3)
    cell = domain.Cell(domain.Coordinate(0, 0))
    cell.ship = ship

    cell.hit()

    assert cell.is_shot
    assert ship.hp == 2


def test_cell_without_ship_is_shot():
    cell = domain.Cell(domain.Coordinate(0, 0))

    cell.hit()

    assert cell.is_shot


def test_cell_cannot_be_shot_twice():
    cell = domain.Cell(domain.Coordinate(0, 0))
    cell.hit()

    with pytest.raises(errors.CellAlreadyShot):
        cell.hit()


def test_cell_cannot_assign_ship_twice():
    cell = domain.Cell(domain.Coordinate(0, 0))
    ship = domain.Ship("id", type="ship", hp=3)
    another_ship = domain.Ship("id", type="ship", hp=3)

    cell.set_ship(ship)

    with pytest.raises(errors.CellTaken):
        cell.set_ship(another_ship)


def test_cell_has_correct_col_and_row():
    cell = domain.Cell(domain.Coordinate(0, 0))

    assert cell.col == "A"
    assert cell.row == 1
