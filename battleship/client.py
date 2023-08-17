# type: ignore
import argparse
import json

from rich.console import Console
from rich.prompt import Prompt
from websockets.sync.client import ClientConnection, connect

from battleship.server import GameEvent

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="localhost")
parser.add_argument("--port", type=int, default=8000)

console = Console()

connection = None


def send_new_player(nickname: str, ws: ClientConnection) -> None:
    ws.send(json.dumps({"kind": GameEvent.NEW_PLAYER, "payload": {"nickname": nickname}}))


def run_client(host: str, port: int) -> None:
    nickname = Prompt.ask("Your nickname")

    with connect(f"ws://{host}:{port}") as ws:
        send_new_player(nickname, ws)
        console.print(f"Connected to the server as {nickname}")

        for message in ws:
            print(message)


if __name__ == "__main__":
    args = parser.parse_args()
    try:
        run_client(args.host, args.port)
    except KeyboardInterrupt:
        connection.close()
