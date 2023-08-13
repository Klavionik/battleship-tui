import pytest

from battleship import domain, errors


def test_ship_hit_decreases_hitpoints():
    ship = domain.Ship(kind="ship", hp=4)

    ship.hit()

    assert ship.hp == 3

    ship.hit()

    assert ship.hp == 2


def test_ship_not_hit_after_no_hp_left():
    ship = domain.Ship(kind="ship", hp=1)

    ship.hit()

    assert ship.hp == 0

    ship.hit()

    assert ship.hp == 0


def test_ship_with_no_hp_is_dead():
    ship = domain.Ship(kind="ship", hp=1)

    ship.hit()

    assert ship.is_dead


def test_cell_hits_bound_ship():
    ship = domain.Ship(kind="ship", hp=3)
    cell = domain.Cell("A", 1, ship)

    cell.hit()

    assert cell.is_shot
    assert ship.hp == 2


def test_cell_without_ship_is_shot():
    cell = domain.Cell("A", 1)

    cell.hit()

    assert cell.is_shot


def test_board_is_10_x_10():
    board = domain.Board()

    assert len(board.cells) == 10

    for row in board.cells:
        assert len(row) == 10


@pytest.mark.parametrize(["row", "col"], [[3, "A"], [5, "B"], [10, "I"]])
def test_board_find_cells(row: str, col: str):
    board = domain.Board()

    cell = board.find_cell(f"{col}{row}")

    assert cell.col == col
    assert cell.row == row


@pytest.mark.parametrize(["row", "col"], [[11, "A"], [0, "B"], [5, "V"]])
def test_board_raises_exc_if_cell_not_found(row: str, col: str):
    board = domain.Board()

    with pytest.raises(errors.CellNotFound):
        board.find_cell(f"{col}{row}")


def test_board_places_ship():
    board = domain.Board()
    ship = domain.Ship(kind="ship", hp=3)

    board.place_ship("A3", "A4", "A5", ship=ship)

    assert board.cells[2][0].ship is ship
    assert board.cells[3][0].ship is ship
    assert board.cells[4][0].ship is ship


def test_board_raises_exc_if_cell_is_taken():
    board = domain.Board()
    ship = domain.Ship(kind="ship", hp=3)
    another_ship = domain.Ship(kind="ship", hp=3)

    board.place_ship("A3", "A4", "A5", ship=ship)

    with pytest.raises(errors.CellTaken):
        board.place_ship("A3", "A4", "A5", ship=another_ship)

    with pytest.raises(errors.CellTaken):
        board.place_ship("A5", "A6", "A7", ship=another_ship)

    with pytest.raises(errors.CellTaken):
        board.place_ship("A5", "B5", "C5", ship=another_ship)


def test_board_shooting():
    board = domain.Board()
    ship = domain.Ship(kind="ship", hp=4)
    board.place_ship("J7", "J8", "J9", "J10", ship=ship)

    board.shoot("J7")

    assert ship.hp == 3

    board.shoot("J6")

    assert ship.hp == 3
