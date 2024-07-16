import pytest

from battleship.engine import domain
from battleship.engine import rosters as rosters


@rosters.register
def test():
    return [
        ("ship", 2),
    ]


@pytest.fixture
def roster():
    return rosters.get_roster("test")


@pytest.fixture
def game(roster) -> domain.Game:
    player_a = domain.Player(name="player_a")
    player_b = domain.Player(name="player_b")
    return domain.Game(player_a, player_b, roster)
