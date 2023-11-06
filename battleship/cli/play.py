import enum
from typing import Annotated

import typer

from battleship import tui
from battleship.cli.console import get_console
from battleship.engine import create_game
from battleship.engine.domain import FiringOrder
from battleship.engine.roster import get_roster

app = typer.Typer()
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
    singleplayer_app = tui.BattleshipApp.singleplayer(game)

    tui.run(singleplayer_app)
