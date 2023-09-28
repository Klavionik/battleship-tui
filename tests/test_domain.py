import pytest

from battleship.engine import domain, errors

TEST_SHIP_SUITE = [
    ("ship", 2),
]


def test_ship_can_be_damaged():
    ship = domain.Ship(type="ship", hp=4)

    ship.damage()

    assert ship.hp == 3

    ship.damage()

    assert ship.hp == 2


def test_ship_no_damage_after_no_hp_left():
    ship = domain.Ship(type="ship", hp=1)

    ship.damage()

    assert ship.hp == 0

    ship.damage()

    assert ship.hp == 0


def test_ship_with_no_hp_is_destroyed():
    ship = domain.Ship(type="ship", hp=1)

    ship.damage()

    assert ship.destroyed


def test_cell_can_be_assigned_ship():
    ship = domain.Ship(type="ship", hp=1)
    cell = domain.Cell("A", 1)

    cell.assign_ship(ship)

    assert cell.ship is ship


def test_cell_hits_bound_ship():
    ship = domain.Ship(type="ship", hp=3)
    cell = domain.Cell("A", 1)
    cell.ship = ship

    cell.hit()

    assert cell.is_shot
    assert ship.hp == 2


def test_cell_without_ship_is_shot():
    cell = domain.Cell("A", 1)

    cell.hit()

    assert cell.is_shot


def test_cell_cannot_be_shot_twice():
    cell = domain.Cell("A", 1)
    cell.hit()

    with pytest.raises(errors.CellAlreadyShot):
        cell.hit()


def test_cell_cannot_assign_ship_twice():
    cell = domain.Cell("A", 1)
    ship = domain.Ship(type="ship", hp=3)
    another_ship = domain.Ship(type="ship", hp=3)

    cell.assign_ship(ship)

    with pytest.raises(errors.CellTaken):
        cell.assign_ship(another_ship)


@pytest.mark.parametrize("coord", ["A3", "B5", "I10"])
def test_board_find_cells(coord: str):
    board = domain.Board()

    cell = board[coord]

    assert cell.coordinate == coord


@pytest.mark.parametrize("coord", ["A11", "B0", "V5"])
def test_board_raises_exc_if_cell_not_found(coord):
    board = domain.Board()

    with pytest.raises(errors.CellOutOfRange):
        _ = board[coord]


@pytest.mark.parametrize("bad_coord", ["", "meow", "11A", None])
def test_board_raises_exc_if_coord_incorrect(bad_coord):
    board = domain.Board()

    with pytest.raises(errors.IncorrectCoordinate):
        _ = board[bad_coord]


def test_board_places_ship():
    board = domain.Board()
    ship = domain.Ship(type="ship", hp=3)

    board.place_ship(["A3", "A4", "A5"], ship=ship)
    cell_a3 = board["A3"]
    cell_a4 = board["A4"]
    cell_a5 = board["A5"]

    assert ship in board
    assert cell_a3.ship is ship
    assert cell_a4.ship is ship
    assert cell_a5.ship is ship


def test_board_raises_exc_if_ship_and_cells_dont_match():
    board = domain.Board()
    ship = domain.Ship(type="ship", hp=3)

    with pytest.raises(errors.ShipDoesntFitCells):
        board.place_ship(["A1", "A2"], ship=ship)


def test_board_raises_exc_if_invalid_position():
    board = domain.Board()
    ship = domain.Ship(type="ship", hp=3)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(["A1", "A2", "A4"], ship=ship)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(["B1", "C1", "E1"], ship=ship)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(["B1", "C1", "C3"], ship=ship)


def test_board_can_test_only_ship_membership():
    board = domain.Board()

    with pytest.raises(TypeError):
        _ = "something" in board  # noqa


def test_board_shooting():
    board = domain.Board()
    ship = domain.Ship(type="ship", hp=4)
    board.place_ship(["J7", "J8", "J9", "J10"], ship=ship)

    board.hit_cell("J7")

    assert ship.hp == 3

    board.hit_cell("J6")

    assert ship.hp == 3


def test_player_ships_left_returns_alive_ships():
    board = domain.Board()
    player = domain.Player(name="player", board=board)
    ship = domain.Ship(type="ship", hp=2)
    board.place_ship(["A3", "A4"], ship=ship)

    assert player.ships_alive == 1

    board.hit_cell("A3")

    assert player.ships_alive == 1

    board.hit_cell("A4")

    assert player.ships_alive == 0


def test_turn_strikes_hostile_ship():
    player_a_board = domain.Board()
    player_a = domain.Player(name="player_a", board=player_a_board)
    player_b = domain.Player(name="player_b", board=domain.Board())
    ship = domain.Ship(type="ship", hp=2)
    player_a_board.place_ship(["A3", "A4"], ship=ship)
    turn = domain.Turn(player=player_b, hostile=player_a)

    hit_ship = turn.strike("A3")

    assert hit_ship is ship

    nothing = turn.strike("B10")

    assert nothing is None


def test_game_can_place_ship():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_b = domain.Player(name="player_b", board=domain.Board())
    game = domain.Game(player_a, player_b, TEST_SHIP_SUITE)

    game.add_ship(player_a, position=["A3", "A4"], ship_type="ship")

    assert domain.Ship("ship", 2) in player_a.board


def test_game_raises_exc_if_ship_limit_exceeded():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_b = domain.Player(name="player_b", board=domain.Board())
    game = domain.Game(player_a, player_b, TEST_SHIP_SUITE)

    game.add_ship(player_a, position=["A3", "A4"], ship_type="ship")

    with pytest.raises(errors.ShipLimitExceeded):
        game.add_ship(player_a, position=["A3", "A4"], ship_type="ship")


def test_game_raises_exc_if_ship_type_is_not_in_suite():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_b = domain.Player(name="player_b", board=domain.Board())
    game = domain.Game(player_a, player_b, TEST_SHIP_SUITE)

    with pytest.raises(errors.ShipNotFound):
        game.add_ship(player_a, position=["A3", "A4"], ship_type="notship")


def test_player_can_add_ship():
    player = domain.Player("player", board=domain.Board())
    ship = domain.Ship("ship", 2)

    player.add_ship(["A2", "A3"], ship)

    assert ship in player.board


def test_player_can_count_ships_by_type():
    player = domain.Player("player", board=domain.Board())

    assert player.count_ships(ship_type="ship") == 0

    player.add_ship(["A2", "A3"], domain.Ship("ship", 2))

    assert player.count_ships(ship_type="ship") == 1


def test_game_fleet_not_ready():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_b = domain.Player(name="player_b", board=domain.Board())
    game = domain.Game(player_a, player_b, TEST_SHIP_SUITE)

    assert not game.is_fleet_ready(player_a)


def test_game_fleet_ready():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_b = domain.Player(name="player_b", board=domain.Board())
    game = domain.Game(player_a, player_b, TEST_SHIP_SUITE + TEST_SHIP_SUITE)

    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")

    assert not game.is_fleet_ready(player_a)

    game.add_ship(player_a, position=["B2", "B3"], ship_type="ship")

    assert game.is_fleet_ready(player_a)
