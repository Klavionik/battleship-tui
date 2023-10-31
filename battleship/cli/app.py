from typer import Typer

from battleship.cli import account, play

app = Typer(name="Battleship CLI")
app.add_typer(account.app, name="account")
app.add_typer(play.app, name="play")


if __name__ == "__main__":
    app()
