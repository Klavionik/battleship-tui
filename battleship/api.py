from typing import Iterable

from battleship.engine import domain


def new_game(
    player_a_name: str, player_b_name: str, suite: Iterable[domain.ShipConfig] | None = None
) -> domain.Game:
    suite = suite or domain.CLASSIC_SHIP_SUITE
    player_a = domain.Player(name=player_a_name, board=domain.Board())
    player_b = domain.Player(name=player_b_name, board=domain.Board())
    return domain.Game(player_a, player_b, suite)
