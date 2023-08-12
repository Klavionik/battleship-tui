from battleship import api


def run_game():
    player_a_name = input("Player A name\n")
    player_b_name = input("Player B name\n")

    game = api.new_game(player_a_name, player_b_name)
    player_a_ships = api.spawn_ships()

    for ship in player_a_ships:
        ship_cells = input(f"Place {player_a_name}'s {ship.kind}\n").split()
        game.player_a.place_ship(*ship_cells, ship=ship)

    player_b_ships = api.spawn_ships()

    for ship in player_b_ships:
        ship_cells = input(f"Place {game.player_b}'s {ship.kind}\n").split()
        game.player_b.place_ship(*ship_cells, ship=ship)

    for turn in game:
        coord = input(f"{turn.player}'s turn: ")
        cell = turn.fire(coord)

        if cell.ship is None:
            print("Miss!")
            continue

        if cell.ship.is_dead:
            print(f"{turn.hostile}'s {cell.ship.kind} destroyed!")
        else:
            print(f"{turn.hostile}'s ship is hit!")

    print(f"{game.winner} has won!")
