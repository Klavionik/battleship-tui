from battleship.engine.domain import Coordinate


def test_from_human():
    coor = Coordinate.from_human("A2")

    assert coor.x == 0
    assert coor.y == 1
    assert coor.col == "A"
    assert coor.row == 2


def test_to_human():
    coor = Coordinate(0, 0)

    assert coor.to_human() == "A1"


def test_adjacent_coordinates():
    expected = [Coordinate(0, -1), Coordinate(1, 0), Coordinate(0, 1), Coordinate(-1, 0)]

    coor = Coordinate(0, 0)

    assert [coor.up(), coor.right(), coor.down(), coor.left()] == expected
