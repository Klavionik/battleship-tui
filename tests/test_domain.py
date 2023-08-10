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
