from battleship import domain


def test_ship_hit_decreases_hitpoints():
    battleship = domain.Battleship()

    battleship.hit()

    assert battleship.hitpoints == 3


def test_ship_hit_but_no_hp_left():
    battleship = domain.Battleship()

    battleship.hit()
    battleship.hit()
    battleship.hit()
    battleship.hit()

    assert battleship.hitpoints == 0

    battleship.hit()

    assert battleship.hitpoints == 0
