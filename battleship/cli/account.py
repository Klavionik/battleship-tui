from typing import Annotated, Any, Generator

import typer
from httpx import Client
from typer import Exit, Option, Typer

from battleship import get_client_version
from battleship.cli.console import get_console

app = Typer(help="Manage multiplayer account.")
console = get_console()


def _unpack_400_errors(errors: list[dict[str, Any]]) -> Generator[tuple[str, str], None, None]:
    for error in errors:
        fields = ", ".join(error["loc"])
        msg = error["msg"]
        yield fields, msg


@app.command(help="Register a new account.")
def signup(
    ctx: typer.Context,
    email: Annotated[str, Option(prompt=True, help="Your email.")],
    nickname: Annotated[str, Option(prompt=True, help="Your nickname/display name, 7-20 chars.")],
    password: Annotated[
        str,
        Option(
            prompt=True,
            confirmation_prompt=True,
            hide_input=True,
            help="Your password (min. 9 chars).",
        ),
    ],
) -> None:
    server_url = ctx.obj["server_url"]

    with console.status(f"Creating user {nickname}..."):
        creds = dict(email=email, nickname=nickname, password=password)

        with Client(
            base_url=server_url, headers={"X-Client-Version": get_client_version()}
        ) as client:
            response = client.post("/signup", json=creds)

        if response.status_code != 201:
            console.error(f"Cannot create this user. Error code {response.status_code}.")

            if response.status_code == 400:
                try:
                    errors = response.json()
                except Exception:
                    pass
                else:
                    for fields, msg in _unpack_400_errors(errors):
                        console.print(f"Fields: [accent]{fields}[/]. Reason: [accent]{msg}[/]")

            raise Exit(code=1)

    console.success(f"Signed up as {nickname}. Check your inbox for confirmation email.")
    console.print(
        "[b]Note: without confirmation you won't" " be able to restore access to your account![/]"
    )
