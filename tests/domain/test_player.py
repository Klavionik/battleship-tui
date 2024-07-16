from battleship.engine import domain


def test_player_ships_left_returns_alive_ships():
    player = domain.Player(name="player")
    player.add_ship(
        domain.position_to_coordinates(["A3", "A4"]), domain.Ship("id", type="ship", hp=2)
    )

    assert player.ships_alive == 1

    player.attack(domain.Coordinate.from_human("A3"))

    assert player.ships_alive == 1

    player.attack(domain.Coordinate.from_human("A4"))

    assert player.ships_alive == 0


def test_player_can_add_ship():
    player = domain.Player("player")
    ship = domain.Ship("id", "ship", 2)

    player.add_ship(domain.position_to_coordinates(["A2", "A3"]), ship)

    assert ship in player.ships


def test_player_can_count_ships_by_type():
    player = domain.Player("player")

    assert player.count_ships(ship_type="ship") == 0

    player.add_ship(domain.position_to_coordinates(["A2", "A3"]), domain.Ship("id", "ship", 2))

    assert player.count_ships(ship_type="ship") == 1
