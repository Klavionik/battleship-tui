from battleship import domain


def new_game(player_a_name, player_b_name):
    player_a = domain.Player(name=player_a_name, board=domain.Board())
    player_b = domain.Player(name=player_b_name, board=domain.Board())
    return domain.Game(player_a, player_b)


def spawn_ships():
    return [
        domain.Carrier(),
        domain.Battleship(),
        domain.Cruiser(),
        domain.Submarine(),
        domain.Destroyer()
    ]
