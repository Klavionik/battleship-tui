from battleship import api


def run_game() -> None:
    player_a_name = input("Player A name\n")
    player_b_name = input("Player B name\n")

    game = api.new_game(player_a_name, player_b_name)

    for ship, spawn in game.spawn_ships(player_a_name):
        position = input(f"Place {player_a_name}'s {ship}\n").split()
        spawn(position)

    for ship, spawn in game.spawn_ships(player_b_name):
        position = input(f"Place {player_b_name}'s {ship}\n").split()
        spawn(position)

    for turn in game:
        coord = input(f"{turn.player}'s turn: ")
        hit_ship = turn.strike(coord)

        if hit_ship is None:
            print("Miss!")
            continue

        if hit_ship.destroyed:
            print(f"{turn.hostile}'s {hit_ship.kind} destroyed!")
        else:
            print(f"{turn.hostile}'s ship is hit!")

    print(f"{game.winner} has won!")
