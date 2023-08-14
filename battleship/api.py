from typing import Iterable, TypeAlias

from battleship import domain

Kind: TypeAlias = str
Hitpoints: TypeAlias = int
Ship: TypeAlias = tuple[Kind, Hitpoints]

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


def spawn_ships(suite: Iterable[Ship] | None = None) -> list[domain.Ship]:
    suite = suite or CLASSIC_SHIP_SUITE
    return [domain.Ship(kind=kind, hp=hp) for kind, hp in suite]
