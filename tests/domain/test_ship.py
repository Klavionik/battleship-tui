from battleship.engine import domain


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
