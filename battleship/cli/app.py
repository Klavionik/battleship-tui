from typer import Typer

from battleship.cli import account

app = Typer(name="Battleship CLI")
app.add_typer(account.app, name="account")


if __name__ == "__main__":
    app()
