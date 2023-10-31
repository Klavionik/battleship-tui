import typer
from typer import Typer

from battleship.cli import account, play
from battleship.tui.app import BattleshipApp

app = Typer(name="Battleship CLI")
app.add_typer(account.app, name="account")
app.add_typer(play.app, name="play")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        BattleshipApp().run()
