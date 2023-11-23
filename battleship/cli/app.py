from typing import Annotated

import typer
from xdg_base_dirs import xdg_data_home

from battleship import get_client_version, tui
from battleship.cli import account, di, logging, play

app = typer.Typer(name="Battleship TUI")
app.add_typer(account.app, name="account")
app.add_typer(play.app, name="play")

DEFAULT_LOG_SINK = xdg_data_home() / "battleship" / "client.log"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    credentials_provider: Annotated[
        str,
        typer.Option(
            envvar="BATTLESHIP_CREDENTIALS_PROVIDER",
            show_envvar=False,
            help="Set multiplayer credentials provider.",
        ),
    ] = "battleship.client:filesystem_credentials_provider",
    server_url: Annotated[
        str,
        typer.Option(envvar="BATTLESHIP_SERVER_URL", show_envvar=False, help="Set server URL."),
    ] = "https://battleship.klavionik.dev",
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
) -> None:
    """
    Battleship TUI is an implementation of the popular paper-and-pen Battleship game for
    your terminal. You can play against the AI or a real player via the Internet,
    customize game options and appearance, keep track of your achievements, and more.
    """

    ctx.ensure_object(dict)
    ctx.obj["server_url"] = server_url

    logging.configure_logger(str(DEFAULT_LOG_SINK))
    config = tui.Config(server_url=server_url, credentials_provider=credentials_provider)
    di.configure_injection(config)

    if version:
        typer.echo(get_client_version())
        raise typer.Exit

    if ctx.invoked_subcommand is None:
        tui.run()
