# mypy: ignore-errors
import argparse
import dataclasses
import json
import secrets
from enum import StrEnum
from typing import Any, Iterator, Optional

from loguru import logger
from websockets.sync.server import ServerConnection, serve

from battleship import domain

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="localhost")
parser.add_argument("--port", type=int, default=8000)


class GameEvent(StrEnum):
    LOGIN = "login"
    LOGGED_IN = "logged_in"
    LOGOUT = "logout"
    NEW_GAME = "new_game"
    NEW_GAME_CREATED = "new_game_created"
    JOIN_GAME = "join_game"
    PLAYER_JOINED = "player_joined"
    PLACE_SHIP = "place_ship"
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
players: dict["ConnectionHandler", Player] = dict()
queue: dict[str, Session] = dict()
games: dict[str, Session] = dict()


@dataclasses.dataclass
class Event:
    kind: GameEvent
    payload: dict[str, Any] = dataclasses.field(default_factory=dict)


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
            logger.info(event)
            match event:
                case Event(kind=GameEvent.LOGIN):
                    player = Player(event.payload["nickname"])
                    players[self] = player
                    self.send_event(
                        Event(kind=GameEvent.LOGGED_IN, payload={"nickname": player.nickname})
                    )
                case Event(kind=GameEvent.LOGOUT):
                    players.pop(self)
                case Event(kind=GameEvent.NEW_GAME):
                    session = Session(secrets.token_urlsafe(8), players[self])
                    queue[session.id] = session

                    for connection in connections:
                        connection.send_event(
                            Event(
                                kind=GameEvent.NEW_GAME_CREATED,
                                payload={"host": session.host, "id": session.id},
                            )
                        )

        logger.info("Connection closed")
        connections.remove(self)


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
