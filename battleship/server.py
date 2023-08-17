# type: ignore
import argparse
import dataclasses
import json
from enum import StrEnum
from typing import Any, Iterator, Optional

from loguru import logger
from websockets.sync.server import ServerConnection, serve

from battleship import domain

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="localhost")
parser.add_argument("--port", type=int, default=8000)


class GameEvent(StrEnum):
    NEW_PLAYER = "new_player"
    NEW_GAME = "new_game"
    PLAYERS_CONNECTED = "players_connected"
    SHIP_PLACED = "ship_placed"
    GAME_READY = "game_ready"
    PLAYER_MOVE = "player_move"
    GAME_ENDED = "game_ended"


class Player:
    def __init__(self, nickname: str):
        self.nickname = nickname


class Session:
    def __init__(self, id: str, host: Player):
        self.id = id
        self.host = host
        self.player: Optional[Player] = None
        self.game: Optional[domain.Game] = None

    def start(self, player: Player):
        self.player = player
        self.game = domain.Game(
            domain.Player(self.host.nickname, domain.Board()),
            domain.Player(self.player.nickname, domain.Board()),
            domain.CLASSIC_SHIP_SUITE,
        )
        return self.game


connections: set["ConnectionHandler"] = set()
players: set[Player] = set()
queue: list[Session] = list()
games: dict[str, Session] = dict()


@dataclasses.dataclass
class Event:
    kind: GameEvent
    payload: dict[str, Any]


class ConnectionHandler:
    def __init__(self):
        self._connection: Optional[ServerConnection] = None

    def close(self):
        self._connection.close()

    def send_event(self, event: Event):
        self._connection.send(json.dumps(dataclasses.asdict(event)))

    def events(self) -> Iterator[Event]:
        for message in self._connection:
            yield Event(**json.loads(message))

    def __call__(self, connection: ServerConnection):
        logger.info("New connection received")
        connections.add(self)

        self._connection = connection

        for event in self.events():
            logger.info(f"New event {event}")
            match event:
                case Event(kind=GameEvent.NEW_PLAYER):
                    player = Player(event.payload["nickname"])
                    players.add(player)
                    logger.info(f"New player {player.nickname}")

        logger.info("Connection closed")


def run_server(host: str, port: int) -> None:
    try:
        with serve(ConnectionHandler(), host=host, port=port) as server:
            logger.info(f"Serving at {host}:{port}")
            server.serve_forever()
    except KeyboardInterrupt:
        for connection in connections:
            logger.info(f"Closing connection with {connection._connection.local_address}")
            connection.close()

        logger.info("Server shut down.")


if __name__ == "__main__":
    args = parser.parse_args()
    run_server(args.host, args.port)
