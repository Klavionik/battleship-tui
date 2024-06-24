from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer

from battleship import data_home, get_client_version, tui
from battleship.cli import account, logging, play, settings
from battleship.tui import di

app = typer.Typer(name="Battleship TUI")
app.add_typer(account.app, name="account")
app.add_typer(play.app, name="play")
app.add_typer(settings.app, name="settings")

SENTRY_DSN = "https://e2b5c0eacebf1c8465e440575e4151d1@o579215.ingest.us.sentry.io/4507262636654592"


def make_log_sink(debug: bool) -> str:
    now = datetime.now(tz=timezone.utc)

    if debug:
        log_home = Path()
    else:
        log_home = data_home
    return str(log_home / f"client_{now:%Y-%m-%d_%H-%M-%S}.log")


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
    settings_provider: Annotated[
        str,
        typer.Option(
            envvar="BATTLESHIP_SETTINGS_PROVIDER",
            show_envvar=False,
            help="Set game settings provider.",
        ),
    ] = "battleship.tui.settings:filesystem_settings_provider",
    server_url: Annotated[
        str,
        typer.Option(envvar="BATTLESHIP_SERVER_URL", show_envvar=False, help="Set server URL."),
    ] = "https://battleship.klavionik.dev",
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
    debug: Annotated[
        bool, typer.Option(envvar="BATTLESHIP_DEBUG", show_envvar=False, help="Enable debug mode.")
    ] = False,
) -> None:
    """
    Battleship TUI is an implementation of the popular paper-and-pen Battleship game for
    your terminal. You can play against the computer or a real player via the Internet,
    customize game options and appearance, keep track of your achievements, and more.
    """

    ctx.ensure_object(dict)
    ctx.obj["server_url"] = server_url
    ctx.obj["debug"] = debug

    logging.configure_logger(make_log_sink(debug))
    logging.configure_sentry(SENTRY_DSN)
    config = tui.Config(
        server_url=server_url,
        credentials_provider=credentials_provider,
        game_settings_provider=settings_provider,
    )
    di.configure_injection(config)

    if version:
        typer.echo(get_client_version())
        raise typer.Exit

    if ctx.invoked_subcommand is None:
        tui.run(debug=debug)


def run() -> None:
    try:
        app()
    except tui.BattleshipError as exc:
        raise SystemExit(str(exc))
