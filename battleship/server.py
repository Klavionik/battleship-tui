# mypy: ignore-errors
import argparse
import json
import secrets
from typing import Iterator, Optional

from loguru import logger
from websockets.sync.server import ServerConnection, serve

from battleship import domain
from battleship.shared.events import ClientEvent, EventMessage, ServerEvent

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="localhost")
parser.add_argument("--port", type=int, default=8000)


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


class ConnectionHandler:
    def __init__(self):
        self._connection: Optional[ServerConnection] = None

    def close(self):
        self._connection.close()

    def send_event(self, event: EventMessage):
        self._connection.send(event.as_json())

    def events(self) -> Iterator[EventMessage]:
        for message in self._connection:
            yield EventMessage(**json.loads(message))

    def __call__(self, connection: ServerConnection):
        logger.info("New connection received")
        connections.add(self)

        self._connection = connection

        for event in self.events():
            logger.info(event)
            match event:
                case EventMessage(kind=ClientEvent.LOGIN):
                    player = Player(event.payload["nickname"])
                    players[self] = player
                    self.send_event(
                        EventMessage(kind=ServerEvent.LOGIN, payload={"nickname": player.nickname})
                    )
                case EventMessage(kind=ClientEvent.LOGOUT):
                    players.pop(self)
                case EventMessage(kind=ClientEvent.NEW_GAME):
                    session = Session(secrets.token_urlsafe(8), players[self])
                    queue[session.id] = session

                    for connection in connections:
                        connection.send_event(
                            EventMessage(
                                kind=ServerEvent.NEW_GAME,
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
