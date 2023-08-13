from typing import Iterable

from battleship import domain

Ship = tuple[str, int]

CLASSIC_SHIP_SUITE = [
    ("carrier", 5),
    ("battleship", 4),
    ("cruiser", 3),
    ("submarine", 3),
    ("destroyer", 2),
]


def new_game(player_a_name: str, player_b_name: str) -> domain.Game:
    player_a = domain.Player(name=player_a_name, board=domain.Board())
    player_b = domain.Player(name=player_b_name, board=domain.Board())
    return domain.Game(player_a, player_b)


def spawn_ships(ships: Iterable[Ship]) -> list[domain.Ship]:
    return [domain.Ship(kind=kind, hp=hp) for kind, hp in ships]
