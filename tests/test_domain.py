import pytest

from battleship import domain, errors


def test_ship_can_be_damaged():
    ship = domain.Ship(kind="ship", hp=4)

    ship.damage()

    assert ship.hp == 3

    ship.damage()

    assert ship.hp == 2


def test_ship_no_damage_after_no_hp_left():
    ship = domain.Ship(kind="ship", hp=1)

    ship.damage()

    assert ship.hp == 0

    ship.damage()

    assert ship.hp == 0


def test_ship_with_no_hp_is_destroyed():
    ship = domain.Ship(kind="ship", hp=1)

    ship.damage()

    assert ship.destroyed


def test_cell_can_be_assigned_ship():
    ship = domain.Ship(kind="ship", hp=1)
    cell = domain.Cell("A", 1)

    cell.assign_ship(ship)

    assert cell.ship is ship


def test_cell_hits_bound_ship():
    ship = domain.Ship(kind="ship", hp=3)
    cell = domain.Cell("A", 1)
    cell.ship = ship

    cell.hit()

    assert cell.is_shot
    assert ship.hp == 2


def test_cell_without_ship_is_shot():
    cell = domain.Cell("A", 1)

    cell.hit()

    assert cell.is_shot


def test_cell_shot_twice_raises_exc():
    cell = domain.Cell("A", 1)
    cell.hit()

    with pytest.raises(errors.CellAlreadyShot):
        cell.hit()


@pytest.mark.parametrize("coord", ["A3", "B5", "I10"])
def test_grid_find_cells(coord: str):
    grid = domain.Grid()

    cell = grid[coord]

    assert cell.coordinate == coord


@pytest.mark.parametrize("coord", ["A11", "B0", "V5"])
def test_grid_raises_exc_if_cell_not_found(coord):
    grid = domain.Grid()

    with pytest.raises(errors.CellOutOfRange):
        _ = grid[coord]


@pytest.mark.parametrize("bad_coord", ["", "meow", "11A", None])
def test_grid_raises_exc_if_coord_incorrect(bad_coord):
    grid = domain.Grid()

    with pytest.raises(errors.IncorrectCoordinate):
        _ = grid[bad_coord]


def test_board_places_ship():
    board = domain.Board()
    ship = domain.Ship(kind="ship", hp=3)

    board.place_ship("A3", "A4", "A5", ship=ship)
    cell_a3 = board.grid["A3"]
    cell_a4 = board.grid["A4"]
    cell_a5 = board.grid["A5"]

    assert ship in board
    assert cell_a3.ship is ship
    assert cell_a4.ship is ship
    assert cell_a5.ship is ship


def test_board_can_test_only_ship_membership():
    board = domain.Board()

    with pytest.raises(TypeError):
        _ = "something" in board  # noqa


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

    board.hit_cell("J7")

    assert ship.hp == 3

    board.hit_cell("J6")

    assert ship.hp == 3


def test_player_can_place_ship():
    board = domain.Board()
    player = domain.Player(name="player", board=board)
    ship = domain.Ship(kind="ship", hp=2)

    player.place_ship("A3", "A4", ship=ship)

    assert ship in board


def test_player_ships_left_returns_alive_ships():
    board = domain.Board()
    player = domain.Player(name="player", board=board)
    ship = domain.Ship(kind="ship", hp=2)
    player.place_ship("A3", "A4", ship=ship)

    assert player.ships_left == 1

    board.hit_cell("A3")

    assert player.ships_left == 1

    board.hit_cell("A4")

    assert player.ships_left == 0


def test_turn_strikes_hostile_ship():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_b = domain.Player(name="player_b", board=domain.Board())
    ship = domain.Ship(kind="ship", hp=2)
    player_a.place_ship("A3", "A4", ship=ship)
    turn = domain.Turn(player=player_b, hostile=player_a)

    hit_ship = turn.strike("A3")

    assert hit_ship is ship

    nothing = turn.strike("B10")

    assert nothing is None


def test_game_gets_player_by_name():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_b = domain.Player(name="player_b", board=domain.Board())
    game = domain.Game(player_a, player_b)

    player = game.get_player(name="player_a")

    assert player is player_a


def test_game_raises_exc_if_player_not_found():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_b = domain.Player(name="player_b", board=domain.Board())
    game = domain.Game(player_a, player_b)

    with pytest.raises(errors.PlayerNotFound):
        _ = game.get_player("notplayer")


def test_game_alternates_turns_between_players_until_no_ships_left():
    player_a = domain.Player(name="player_a", board=domain.Board())
    player_a.place_ship("A1", ship=domain.Ship(kind="ship", hp=1))
    player_b = domain.Player(name="player_b", board=domain.Board())
    player_b.place_ship("A1", ship=domain.Ship(kind="ship", hp=1))
    game = domain.Game(player_a, player_b)
    it = iter(game)

    turn = next(it)
    assert turn.player == player_a
    turn.strike("D1")  # Every turn's strike must be called.

    turn = next(it)
    assert turn.player == player_b
    turn.strike("D2")

    turn = next(it)
    assert turn.player == player_a
    turn.strike("D3")

    turn = next(it)
    assert turn.player == player_b
    turn.strike("D4")
