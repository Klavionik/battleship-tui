import random

import pytest

from battleship.engine import domain, errors
from battleship.engine import roster as rosters


@rosters.register
def test():
    return [
        ("ship", 2),
    ]


@pytest.fixture
def roster():
    return rosters.get_roster("test")


@pytest.fixture
def game(roster) -> domain.Game:
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    return domain.Game(player_a, player_b, roster)


def test_ship_can_be_damaged():
    ship = domain.Ship(id="id", type="ship", hp=4)

    ship.damage()

    assert ship.hp == 3

    ship.damage()

    assert ship.hp == 2


def test_ship_no_damage_after_no_hp_left():
    ship = domain.Ship(id="id", type="ship", hp=1)

    ship.damage()

    assert ship.hp == 0

    ship.damage()

    assert ship.hp == 0


def test_ship_with_no_hp_is_destroyed():
    ship = domain.Ship(id="id", type="ship", hp=1)

    ship.damage()

    assert ship.destroyed


def test_cell_can_be_assigned_ship():
    ship = domain.Ship(id="id", type="ship", hp=1)
    cell = domain.Cell("A", 1)

    cell.set_ship(ship)

    assert cell.ship is ship


def test_cell_hits_bound_ship():
    ship = domain.Ship(id="id", type="ship", hp=3)
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
    ship = domain.Ship("id", type="ship", hp=3)
    another_ship = domain.Ship("id", type="ship", hp=3)

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
    ship = domain.Ship("id", type="ship", hp=3)

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
    ship = domain.Ship("id", type="ship", hp=3)

    with pytest.raises(errors.ShipDoesntFitCells):
        board.place_ship(["A1", "A2"], ship=ship)


def test_board_raises_exc_if_invalid_position():
    board = domain.Board()
    ship = domain.Ship("id", type="ship", hp=3)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(["A1", "A2", "A4"], ship=ship)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(["B1", "C1", "E1"], ship=ship)

    with pytest.raises(errors.InvalidPosition):
        board.place_ship(["B1", "C1", "C3"], ship=ship)


def test_board_shooting():
    board = domain.Board()
    ship = domain.Ship("id", type="ship", hp=4)
    board.place_ship(["J7", "J8", "J9", "J10"], ship=ship)

    board.hit_cell("J7")

    assert ship.hp == 3

    board.hit_cell("J6")

    assert ship.hp == 3


def test_player_ships_left_returns_alive_ships():
    player = domain.Player(name="player")
    player.add_ship(["A3", "A4"], ship=domain.Ship("id", type="ship", hp=2))

    assert player.ships_alive == 1

    player.attack("A3")

    assert player.ships_alive == 1

    player.attack("A4")

    assert player.ships_alive == 0


def test_game_can_place_ship(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    [item] = roster
    game = domain.Game(player_a, player_b, roster)

    game.add_ship(player_a, position=["A3", "A4"], roster_id=item.id)

    assert domain.Ship(*item) in player_a.ships


def test_game_raises_exc_if_ship_limit_exceeded(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    [item] = roster
    game = domain.Game(player_a, player_b, roster)

    game.add_ship(player_a, position=["A3", "A4"], roster_id=item.id)

    with pytest.raises(errors.ShipLimitExceeded):
        game.add_ship(player_a, position=["A3", "A4"], roster_id=item.id)


def test_game_raises_exc_if_no_matching_roster_item(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster)

    with pytest.raises(errors.ShipNotFound):
        game.add_ship(player_a, position=["A3", "A4"], roster_id="notid")


def test_player_can_add_ship():
    player = domain.Player("player")
    ship = domain.Ship("id", "ship", 2)

    player.add_ship(["A2", "A3"], ship)

    assert ship in player.ships


def test_player_can_count_ships_by_type():
    player = domain.Player("player")

    assert player.count_ships(ship_type="ship") == 0

    player.add_ship(["A2", "A3"], domain.Ship("id", "ship", 2))

    assert player.count_ships(ship_type="ship") == 1


def test_game_fleet_not_ready(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster)

    assert not game._is_fleet_ready(player_a)


def test_game_fleet_ready(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    double_roster = roster + roster
    [item_1, item_2] = double_roster
    game = domain.Game(player_a, player_b, double_roster)
    fleet_ready = False

    def handler(ship_spawned):
        nonlocal fleet_ready
        fleet_ready = ship_spawned.fleet_ready

    game.on(domain.ShipSpawned, handler)

    game.add_ship(player_a, position=["A2", "A3"], roster_id=item_1.id)

    assert not fleet_ready

    game.add_ship(player_a, position=["B2", "B3"], roster_id=item_2.id)

    assert fleet_ready


def test_game_ready_if_both_fleets_ready(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    [item] = roster
    game = domain.Game(player_a, player_b, roster)

    game.add_ship(player_a, position=["A2", "A3"], roster_id=item.id)

    assert game.state == domain.GameState.ARRANGE_FLEET

    game.add_ship(player_b, position=["A2", "A3"], roster_id=item.id)

    assert game.state == domain.GameState.BATTLE


def test_game_starts_with_arrange_fleet_state(game):
    assert game.state == domain.GameState.ARRANGE_FLEET


def test_game_actor_and_subject_differ(roster):
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster)
    [item] = roster
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item.id)

    assert game.actor is player_a
    assert game.subject is player_b


def test_game_cannot_fire_if_not_started(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster)

    with pytest.raises(errors.GameNotReady):
        game.fire(["A1"])


def test_game_cannot_fire_multiple_shots_if_not_salvo_mode(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    [item] = roster
    game = domain.Game(player_a, player_b, roster)
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item.id)

    with pytest.raises(errors.TooManyShots):
        game.fire(["A1", "A2"])


def test_game_shots_count_must_match_ships_count(roster):
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster, salvo_mode=True)
    [item] = roster
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item.id)

    with pytest.raises(errors.IncorrectShots):
        game.fire(["A1", "A2"])


def test_game_fire_returns_correct_salvo_if_miss(roster):
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster)
    [item] = roster
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item.id)

    salvo = game.fire(["B4"])

    assert len(salvo) == 1

    [shot] = salvo

    assert salvo.actor is player_a
    assert salvo.subject is player_b
    assert shot.miss


def test_game_fire_returns_correct_salvo_if_hit(roster):
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster)
    [item] = roster
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item.id)

    salvo = game.fire(["B2"])

    assert len(salvo) == 1

    [shot] = salvo

    assert salvo.actor is player_a
    assert salvo.subject is player_b
    assert shot.hit


def test_game_fire_returns_correct_salvo_in_salvo_mode(roster):
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    double_roster = roster + roster
    [item_1, item_2] = double_roster
    game = domain.Game(player_a, player_b, double_roster, salvo_mode=True)
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item_1.id)
    game.add_ship(player_a, position=["C4", "D4"], roster_id=item_2.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item_1.id)
    game.add_ship(player_b, position=["F4", "G4"], roster_id=item_2.id)
    attempt_hit: domain.Result  # type: ignore
    attempt_miss: domain.Result  # type: ignore

    salvo = game.fire(["B2", "G5"])

    assert len(salvo) == 2

    attempt_hit, attempt_miss = salvo

    assert salvo.actor is player_a
    assert salvo.subject is player_b
    assert attempt_hit.hit
    assert attempt_miss.miss


def test_game_alternates_players_after_every_shot(roster):
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster)
    [item] = roster
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item.id)

    assert game.actor is player_a
    assert game.subject is player_b

    game.turn(game.fire(["B2"]))

    assert game.actor is player_b
    assert game.subject is player_a

    game.turn(game.fire(["A5"]))

    assert game.actor is player_a
    assert game.subject is player_b


def test_game_alternates_players_after_first_miss(roster):
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    game = domain.Game(player_a, player_b, roster, firing_order=domain.FiringOrder.UNTIL_MISS)
    [item] = roster
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item.id)

    assert game.actor is player_a
    assert game.subject is player_b

    game.turn(game.fire(["B2"]))

    assert game.actor is player_a
    assert game.subject is player_b

    game.turn(game.fire(["B1"]))

    assert game.actor is player_b
    assert game.subject is player_a


def test_game_alternates_players_after_first_miss_salvo_mode(roster):
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    double_roster = roster + roster
    [item_1, item_2] = double_roster
    game = domain.Game(
        player_a,
        player_b,
        double_roster,
        firing_order=domain.FiringOrder.UNTIL_MISS,
        salvo_mode=True,
    )
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item_1.id)
    game.add_ship(player_a, position=["C4", "D4"], roster_id=item_2.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item_1.id)
    game.add_ship(player_b, position=["F4", "G4"], roster_id=item_2.id)

    assert game.actor is player_a
    assert game.subject is player_b

    game.turn(game.fire(["B2", "C3"]))  # One hit, one miss.

    assert game.actor is player_a
    assert game.subject is player_b

    game.turn(game.fire(["B1", "F5"]))  # Both miss.

    assert game.actor is player_b
    assert game.subject is player_a


def test_game_ends_if_player_has_no_more_ships(roster):
    random.seed(42)
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    double_roster = roster + roster
    [item_1, item_2] = double_roster
    game = domain.Game(player_a, player_b, double_roster)
    game.add_ship(player_a, position=["A2", "A3"], roster_id=item_1.id)
    game.add_ship(player_a, position=["C4", "D4"], roster_id=item_2.id)
    game.add_ship(player_b, position=["B2", "B3"], roster_id=item_1.id)
    game.add_ship(player_b, position=["F4", "G4"], roster_id=item_2.id)

    game.turn(game.fire(["B2"]))  # Player A hit.
    game.turn(game.fire(["A4"]))  # Player B missed.
    game.turn(game.fire(["B3"]))  # Player A hit. Ship sunk.
    game.turn(game.fire(["D4"]))  # Player B hit.
    game.turn(game.fire(["F4"]))  # Player A hit.
    game.turn(game.fire(["C4"]))  # Player B hit. Ship sunk.
    game.turn(game.fire(["G4"]))  # Player A hit. Ship sunk.

    assert game.winner is player_a
    assert game.state == domain.GameState.END

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


def test_game_emits_ship_spawned(game, roster):
    [item] = roster
    events = []

    def handler(ship_spawned):
        events.append(ship_spawned)

    game.on(domain.ShipSpawned, handler)

    game.add_ship(game.player_a, ["A2", "A3"], item.id)
    game.add_ship(game.player_b, ["B2", "B3"], item.id)

    assert events == [
        domain.ShipSpawned(game.player_a, item.id, ["A2", "A3"], fleet_ready=True),
        domain.ShipSpawned(game.player_b, item.id, ["B2", "B3"], fleet_ready=True),
    ]


def test_game_emits_next_move_when_ready(game, roster):
    [item] = roster
    events = []

    def handler(next_move):
        events.append(next_move)

    game.on(domain.NextMove, handler)

    game.add_ship(game.player_a, ["A2", "A3"], item.id)
    game.add_ship(game.player_b, ["B2", "B3"], item.id)

    assert events == [domain.NextMove(game.actor, game.subject)]


def test_game_emits_next_move_after_turn(game, roster):
    [item] = roster
    events = []

    def handler(next_move):
        events.append(next_move)

    game.on(domain.NextMove, handler)

    game.add_ship(game.player_a, ["A2", "A3"], item.id)
    game.add_ship(game.player_b, ["B2", "B3"], item.id)

    salvo = game.fire(["A2"])

    assert events == [domain.NextMove(game.actor, game.subject)]
    events.pop()  # Clear events.

    game.turn(salvo)

    assert events == [domain.NextMove(game.actor, game.subject)]


def test_game_emits_game_ended_when_player_wins(game, roster):
    [item] = roster
    events = []

    def handler(game_ended):
        events.append(game_ended)

    game.on(domain.GameEnded, handler)

    game.add_ship(game.player_a, ["A2", "A3"], item.id)
    game.add_ship(game.player_b, ["B2", "B3"], item.id)

    game.turn(game.fire(["A2"]))
    game.turn(game.fire(["B2"]))
    game.turn(game.fire(["A3"]))

    assert events == [domain.GameEnded(game.winner)]
