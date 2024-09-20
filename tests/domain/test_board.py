import pytest

from battleship.engine import domain, errors


@pytest.mark.parametrize("point", [(0, 2), (1, 4), (9, 9)])
def test_board_find_cells(point: str):
    board = domain.Board()
    coor = domain.Coordinate(*point)

    cell = board.get_cell(coor)

    assert cell.coordinate == coor


@pytest.mark.parametrize("coord", ["A11", "B0", "V5"])
def test_board_raises_none_if_cell_not_found(coord):
    board = domain.Board()

    coor = domain.Coordinate.from_human(coord)

    with pytest.raises(errors.CellOutOfRange):
        board.get_cell(coor)


def test_board_places_ship():
    board = domain.Board()
    ship = domain.Ship("id", type="ship", hp=3)
    a3, a4, a5 = domain.position_to_coordinates(["A3", "A4", "A5"])

    board.place_ship([a3, a4, a5], ship=ship)
    cell_a3 = board.get_cell(a3)
    cell_a4 = board.get_cell(a4)
    cell_a5 = board.get_cell(a5)

    assert ship in board.ships
    assert cell_a3.ship is ship
    assert cell_a4.ship is ship
    assert cell_a5.ship is ship


def test_board_raises_exc_if_ship_and_cells_dont_match():
    board = domain.Board()
    ship = domain.Ship("id", type="ship", hp=3)

    with pytest.raises(errors.ShipDoesntFitCells):
        board.place_ship(domain.position_to_coordinates(["A1", "A2"]), ship=ship)


def test_board_raises_exc_if_invalid_position():
    board = domain.Board()
    ship = domain.Ship("id", type="ship", hp=3)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(domain.position_to_coordinates(["A1", "A2", "A4"]), ship=ship)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(domain.position_to_coordinates(["B1", "C1", "E1"]), ship=ship)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(domain.position_to_coordinates(["B1", "C1", "C3"]), ship=ship)


def test_board_shooting():
    board = domain.Board()
    ship = domain.Ship("id", type="ship", hp=4)
    board.place_ship(domain.position_to_coordinates(["J7", "J8", "J9", "J10"]), ship=ship)

    board.hit_cell(domain.Coordinate.from_human("J7"))

    assert ship.hp == 3

    board.hit_cell(domain.Coordinate.from_human("J6"))

    assert ship.hp == 3


@pytest.mark.parametrize(
    "coor", ["F4", "G4", "G5", "G6", "G7", "G8", "E8", "F8", "E7", "E6", "E5", "E4"]
)
def test_board_finds_ships_in_adjacent_cells(coor):
    board = domain.Board()
    board.place_ship(
        domain.position_to_coordinates(["F5", "F6", "F7"]), domain.Ship(id="1", hp=3, type="ship")
    )

    assert board.has_adjacent_ship(domain.Coordinate.from_human(coor))


@pytest.mark.parametrize("coor", ["F3", "F9", "D4"])
def test_board_doesnt_find_ships_in_distant_cells(coor):
    board = domain.Board()
    board.place_ship(
        domain.position_to_coordinates(["F5", "F6", "F7"]), domain.Ship(id="1", hp=3, type="ship")
    )

    assert not board.has_adjacent_ship(domain.Coordinate.from_human(coor))


def test_board_finds_ships_in_adjacent_cells_ignoring_cells_out_of_range():
    board = domain.Board()
    board.place_ship(
        domain.position_to_coordinates(["A1", "A2", "A3"]), domain.Ship(id="1", hp=3, type="ship")
    )

    assert board.has_adjacent_ship(domain.Coordinate.from_human("A4"))
