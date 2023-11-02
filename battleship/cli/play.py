import enum
from typing import Annotated

import typer
from typer import Typer

from battleship.cli.console import get_console
from battleship.engine import create_game
from battleship.engine.domain import FiringOrder
from battleship.engine.roster import get_roster
from battleship.tui.app import BattleshipApp

app = Typer()
console = get_console()


class Roster(enum.StrEnum):
    CLASSIC = enum.auto()
    RUSSIAN = enum.auto()


@app.command()
def single(
    roster: Roster = Roster.CLASSIC,
    firing_order: FiringOrder = FiringOrder.ALTERNATELY,
    salvo_mode: Annotated[bool, typer.Option("--salvo")] = False,
) -> None:
    game = create_game("Player", "Computer", get_roster(roster), firing_order, salvo_mode)
    tui = BattleshipApp.singleplayer(game)
    tui.run()
