from enum import auto
from typing import Annotated

import inject
import typer

from battleship import tui
from battleship.cli.console import get_console
from battleship.client import CredentialsProvider
from battleship.engine.domain import FiringOrder
from battleship.shared.compat import StrEnum

app = typer.Typer(help="Play Battleship TUI.")
multiplayer_app = typer.Typer(help="Start a multiplayer session.")
app.add_typer(multiplayer_app, name="multi")
console = get_console()


class Roster(StrEnum):
    CLASSIC = auto()
    RUSSIAN = auto()


@app.command(help="Start a singleplayer session.")
def single(
    ctx: typer.Context,
    roster: Annotated[
        Roster, typer.Option(help="Choose ships that make up a fleet.")
    ] = Roster.CLASSIC,
    firing_order: Annotated[
        FiringOrder, typer.Option(help="Choose firing order.")
    ] = FiringOrder.ALTERNATELY,
    salvo_mode: Annotated[bool, typer.Option("--salvo", help="Enable salvo mode.")] = False,
) -> None:
    tui_app = tui.BattleshipApp.singleplayer(roster, firing_order, salvo_mode)

    tui.run(tui_app, ctx.obj["debug"])


@multiplayer_app.command(help="Create a new multiplayer session.")
def new(
    ctx: typer.Context,
    game_name: Annotated[
        str, typer.Option(help="Specify game name (leave blank for default).")
    ] = "",
    roster: Annotated[
        Roster, typer.Option(help="Choose ships that make up a fleet.")
    ] = Roster.CLASSIC,
    firing_order: Annotated[
        FiringOrder, typer.Option(help="Choose firing order.")
    ] = FiringOrder.ALTERNATELY,
    salvo_mode: Annotated[bool, typer.Option("--salvo", help="Enable salvo mode.")] = False,
) -> None:
    credentials_provider: CredentialsProvider = inject.instance(CredentialsProvider)
    credentials = credentials_provider.load()

    if credentials is None:
        console.warning(
            "You are not logged in. Please log in using the in-game menu.\n"
            "Then you'll be able to start multiplayer games from the CLI."
        )
        raise typer.Exit(1)

    tui_app = tui.BattleshipApp.multiplayer_new(game_name, roster, firing_order, salvo_mode)

    tui.run(tui_app, ctx.obj["debug"])


@multiplayer_app.command(help="Join a multiplayer session.")
def join(ctx: typer.Context, game_code: str) -> None:
    credentials_provider: CredentialsProvider = inject.instance(CredentialsProvider)
    credentials = credentials_provider.load()

    if credentials is None:
        console.warning(
            "You are not logged in. Please log in using the in-game menu.\n"
            "Then you'll be able to start multiplayer games from the CLI."
        )
        raise typer.Exit(1)

    tui_app = tui.BattleshipApp.multiplayer_join(game_code)

    tui.run(tui_app, ctx.obj["debug"])
