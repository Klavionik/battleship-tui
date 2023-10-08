import random

import pytest

from battleship.engine import domain, errors, roster


@roster.register
def test():
    return [
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

    cell.set_ship(ship)

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

    cell.set_ship(ship)

    with pytest.raises(errors.CellTaken):
        cell.set_ship(another_ship)


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

    assert ship in board.ships
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


def test_board_shooting():
    board = domain.Board()
    ship = domain.Ship(type="ship", hp=4)
    board.place_ship(["J7", "J8", "J9", "J10"], ship=ship)

    board.hit_cell("J7")

    assert ship.hp == 3

    board.hit_cell("J6")

    assert ship.hp == 3


def test_player_ships_left_returns_alive_ships():
    player = domain.Player(name="player")
    player.add_ship(["A3", "A4"], ship=domain.Ship(type="ship", hp=2))

    assert player.ships_alive == 1

    player.attack("A3")

    assert player.ships_alive == 1

    player.attack("A4")

    assert player.ships_alive == 0


def test_game_can_place_ship():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))

    game.add_ship(player_a, position=["A3", "A4"], ship_type="ship")

    assert domain.Ship("ship", 2) in player_a.ships


def test_game_raises_exc_if_ship_limit_exceeded():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))

    game.add_ship(player_a, position=["A3", "A4"], ship_type="ship")

    with pytest.raises(errors.ShipLimitExceeded):
        game.add_ship(player_a, position=["A3", "A4"], ship_type="ship")


def test_game_raises_exc_if_ship_type_is_not_in_suite():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))

    with pytest.raises(errors.ShipNotFound):
        game.add_ship(player_a, position=["A3", "A4"], ship_type="notship")


def test_player_can_add_ship():
    player = domain.Player("player")
    ship = domain.Ship("ship", 2)

    player.add_ship(["A2", "A3"], ship)

    assert ship in player.ships


def test_player_can_count_ships_by_type():
    player = domain.Player("player")

    assert player.count_ships(ship_type="ship") == 0

    player.add_ship(["A2", "A3"], domain.Ship("ship", 2))

    assert player.count_ships(ship_type="ship") == 1


def test_game_fleet_not_ready():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))

    assert not game.is_fleet_ready(player_a)


def test_game_fleet_ready():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test") + roster.get_roster("test"))

    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")

    assert not game.is_fleet_ready(player_a)

    game.add_ship(player_a, position=["B2", "B3"], ship_type="ship")

    assert game.is_fleet_ready(player_a)


def test_game_starts_if_fleets_ready():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_b, position=["A2", "A3"], ship_type="ship")

    game.start()

    assert game.started


def test_game_cannot_start_if_fleets_not_ready():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))

    with pytest.raises(errors.ShipsNotPlaced):
        game.start()

    assert not game.started


def test_game_current_player_and_player_under_attack_differs():
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))

    assert game.current_player is player_a
    assert game.player_under_attack is player_b


def test_game_cannot_fire_if_not_started():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))

    with pytest.raises(errors.GameNotStarted):
        game.fire(["A1"])


def test_game_cannot_fire_multiple_shots_if_not_salvo_mode():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.start()

    with pytest.raises(errors.TooManyShots):
        game.fire(["A1", "A2"])


def test_game_shots_count_must_match_ships_count():
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"), salvo_mode=True)
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.start()

    with pytest.raises(errors.IncorrectShots):
        game.fire(["A1", "A2"])


def test_game_fire_returns_correct_fire_attempt_if_miss():
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.start()
    attempt: domain.Result  # type: ignore

    fire_attempts = game.fire(["B4"])

    assert len(fire_attempts) == 1

    [attempt] = fire_attempts

    assert attempt.actor is player_a
    assert attempt.subject is player_b
    assert attempt.miss


def test_game_fire_returns_correct_fire_attempt_if_hit():
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.start()
    attempt: domain.Result  # type: ignore

    fire_attempts = game.fire(["B2"])

    assert len(fire_attempts) == 1

    [attempt] = fire_attempts

    assert attempt.actor is player_a
    assert attempt.subject is player_b
    assert attempt.hit


def test_game_fire_returns_correct_fire_attempts_salvo_mode():
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(
        player_a, player_b, roster.get_roster("test") + roster.get_roster("test"), salvo_mode=True
    )
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_a, position=["C4", "D4"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.add_ship(player_b, position=["F4", "G4"], ship_type="ship")
    game.start()
    attempt_hit: domain.Result  # type: ignore
    attempt_miss: domain.Result  # type: ignore

    fire_attempts = game.fire(["B2", "G5"])

    assert len(fire_attempts) == 2

    attempt_hit, attempt_miss = fire_attempts

    assert attempt_miss.actor is attempt_hit.actor is player_a
    assert attempt_miss.subject is attempt_hit.subject is player_b
    assert attempt_hit.hit
    assert attempt_miss.miss


def test_game_alternates_players_after_every_shot():
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test"))
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.start()

    assert game.current_player is player_a
    assert game.player_under_attack is player_b

    game.fire(["B2"])

    assert game.current_player is player_b
    assert game.player_under_attack is player_a

    game.fire(["A5"])

    assert game.current_player is player_a
    assert game.player_under_attack is player_b


def test_game_alternates_players_after_first_miss():
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(
        player_a, player_b, roster.get_roster("test"), firing_order=domain.FiringOrder.UNTIL_MISS
    )
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.start()

    assert game.current_player is player_a
    assert game.player_under_attack is player_b

    game.fire(["B2"])

    assert game.current_player is player_a
    assert game.player_under_attack is player_b

    game.fire(["B1"])

    assert game.current_player is player_b
    assert game.player_under_attack is player_a


def test_game_alternates_players_after_first_miss_salve_mode():
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(
        player_a,
        player_b,
        roster.get_roster("test") + roster.get_roster("test"),
        firing_order=domain.FiringOrder.UNTIL_MISS,
        salvo_mode=True,
    )
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_a, position=["C4", "D4"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.add_ship(player_b, position=["F4", "G4"], ship_type="ship")
    game.start()

    assert game.current_player is player_a
    assert game.player_under_attack is player_b

    game.fire(["B2", "C3"])  # One hit, one miss.

    assert game.current_player is player_a
    assert game.player_under_attack is player_b

    game.fire(["B1", "F5"])  # Both miss.

    assert game.current_player is player_b
    assert game.player_under_attack is player_a


def test_game_ends_if_player_has_no_more_ships():
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster.get_roster("test") + roster.get_roster("test"))
    game.add_ship(player_a, position=["A2", "A3"], ship_type="ship")
    game.add_ship(player_a, position=["C4", "D4"], ship_type="ship")
    game.add_ship(player_b, position=["B2", "B3"], ship_type="ship")
    game.add_ship(player_b, position=["F4", "G4"], ship_type="ship")
    game.start()

    game.fire(["B2"])  # Player A hit.
    game.fire(["A4"])  # Player B missed.
    game.fire(["B3"])  # Player A hit. Ship sunk.
    game.fire(["D4"])  # Player B hit.
    game.fire(["F4"])  # Player A hit.
    game.fire(["C4"])  # Player B hit. Ship sunk.
    game.fire(["G4"])  # Player A hit. Ship sunk.

    assert game.winner is player_a
    assert game.ended

    with pytest.raises(errors.GameEnded):
        game.fire(["A1"])


def test_board_gets_adjacent_cell():
    board = domain.Board(size=5)
    cell = domain.Cell(col="B", row=1)

    up = board.get_adjacent_cell(cell, domain.Direction.UP)
    down = board.get_adjacent_cell(cell, domain.Direction.DOWN)
    right = board.get_adjacent_cell(cell, domain.Direction.RIGHT)
    left = board.get_adjacent_cell(cell, domain.Direction.LEFT)

    assert up is None
    assert down.coordinate == "B2"
    assert right.coordinate == "C1"
    assert left.coordinate == "A1"
