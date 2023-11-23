from enum import auto
from typing import Annotated

import typer

from battleship import tui
from battleship.cli.console import get_console
from battleship.engine import create_game
from battleship.engine.domain import FiringOrder
from battleship.engine.roster import get_roster
from battleship.shared.compat import StrEnum

app = typer.Typer(help="Play Battleship TUI.")
console = get_console()


class Roster(StrEnum):
    CLASSIC = auto()
    RUSSIAN = auto()


@app.command(help="Start a singleplayer session.")
def single(
    roster: Annotated[
        Roster, typer.Option(help="Choose ships that make up a fleet.")
    ] = Roster.CLASSIC,
    firing_order: Annotated[
        FiringOrder, typer.Option(help="Choose firing order.")
    ] = FiringOrder.ALTERNATELY,
    salvo_mode: Annotated[bool, typer.Option("--salvo", help="Enable salvo mode.")] = False,
) -> None:
    game = create_game("Player", "Computer", get_roster(roster), firing_order, salvo_mode)
    singleplayer_app = tui.BattleshipApp.singleplayer(game)

    tui.run(singleplayer_app)
