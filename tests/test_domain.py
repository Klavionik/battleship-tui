import pytest

from battleship import domain


def test_ship_hit_decreases_hitpoints():
    carrier = domain.Carrier()
    battleship = domain.Battleship()
    cruiser = domain.Cruiser()
    submarine = domain.Submarine()
    destroyer = domain.Destroyer()

    carrier.hit()
    battleship.hit()
    cruiser.hit()
    submarine.hit()
    destroyer.hit()

    assert carrier.hitpoints == 4
    assert battleship.hitpoints == 3
    assert cruiser.hitpoints == 2
    assert submarine.hitpoints == 2
    assert destroyer.hitpoints == 1


def test_ship_not_hit_after_no_hp_left():
    carrier = domain.Carrier()
    battleship = domain.Battleship()
    cruiser = domain.Cruiser()
    submarine = domain.Submarine()
    destroyer = domain.Destroyer()

    [carrier.hit() for _ in range(carrier.hitpoints + 1)]
    [battleship.hit() for _ in range(battleship.hitpoints + 1)]
    [cruiser.hit() for _ in range(cruiser.hitpoints + 1)]
    [submarine.hit() for _ in range(submarine.hitpoints + 1)]
    [destroyer.hit() for _ in range(destroyer.hitpoints + 1)]

    assert carrier.hitpoints == 0
    assert battleship.hitpoints == 0
    assert cruiser.hitpoints == 0
    assert submarine.hitpoints == 0
    assert destroyer.hitpoints == 0


def test_ship_with_no_hp_is_dead():
    carrier = domain.Carrier()
    battleship = domain.Battleship()
    cruiser = domain.Cruiser()
    submarine = domain.Submarine()
    destroyer = domain.Destroyer()

    [carrier.hit() for _ in range(carrier.hitpoints)]
    [battleship.hit() for _ in range(battleship.hitpoints)]
    [cruiser.hit() for _ in range(cruiser.hitpoints)]
    [submarine.hit() for _ in range(submarine.hitpoints)]
    [destroyer.hit() for _ in range(destroyer.hitpoints)]

    assert carrier.is_dead
    assert battleship.is_dead
    assert cruiser.is_dead
    assert submarine.is_dead
    assert destroyer.is_dead


def test_cell_hits_bound_ship():
    cruiser = domain.Cruiser()
    cell = domain.Cell(1, "A", cruiser)

    cell.hit()

    assert cell.is_shot
    assert cruiser.hitpoints == 2


def test_cell_without_ship_is_shot():
    cell = domain.Cell(1, "A")

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

    assert cell.column == col
    assert cell.row == row


@pytest.mark.parametrize(["row", "col"], [[11, "A"], [0, "B"], [5, "V"]])
def test_board_raises_exc_if_cell_not_found(row: str, col: str):
    board = domain.Board()

    with pytest.raises(domain.CellNotFound):
        board.find_cell(f"{col}{row}")


def test_board_places_ship():
    board = domain.Board()
    ship = domain.Cruiser()

    board.place_ship("A3", "A4", "A5", ship=ship)

    assert board.cells[2][0].ship is ship
    assert board.cells[3][0].ship is ship
    assert board.cells[4][0].ship is ship


def test_board_raises_exc_if_cell_is_taken():
    board = domain.Board()
    ship = domain.Cruiser()
    another_ship = domain.Cruiser()

    board.place_ship("A3", "A4", "A5", ship=ship)

    with pytest.raises(domain.CellTaken):
        board.place_ship("A3", "A4", "A5", ship=another_ship)

    with pytest.raises(domain.CellTaken):
        board.place_ship("A5", "A6", "A7", ship=another_ship)

    with pytest.raises(domain.CellTaken):
        board.place_ship("A5", "B5", "C5", ship=another_ship)
