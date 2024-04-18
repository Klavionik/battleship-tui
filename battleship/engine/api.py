from typing import cast

from battleship.engine.domain import FiringOrder, Game, Player
from battleship.engine.rosters import Roster


def is_firing_order(value: str) -> bool:
    return value in tuple(FiringOrder)


def create_game(
    player_a: str, player_b: str, roster: Roster, firing_order: str, salvo_mode: bool
) -> Game:
    if not is_firing_order(firing_order):
        raise TypeError(f"Firing order {firing_order} is invalid.")

    firing_order = cast(FiringOrder, firing_order)

    return Game(
        player_a=Player(player_a),
        player_b=Player(player_b),
        roster=roster,
        firing_order=firing_order,
        salvo_mode=salvo_mode,
    )
