import argparse
import json
from time import sleep
from typing import Iterator, cast

from loguru import logger
from websockets.sync.server import ServerConnection, serve

from battleship.shared.events import ClientEvent, EventMessage, ServerEvent

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="localhost")
parser.add_argument("--port", type=int, default=8000)


class Player:
    def __init__(self, nickname: str | None):
        self.nickname = nickname or "Guest"


connections: set["ConnectionHandler"] = set()
players: dict["ConnectionHandler", Player] = dict()


class ConnectionHandler:
    def __init__(self) -> None:
        self._connection: ServerConnection = None  # type: ignore

    @property
    def local_address(self) -> tuple[str, int]:
        return cast(tuple[str, int], self._connection.local_address)

    def close(self) -> None:
        self._connection.close()

    def send_event(self, event: EventMessage) -> None:
        self._connection.send(event.as_json())

    def events(self) -> Iterator[EventMessage]:
        for message in self._connection:
            yield EventMessage(**json.loads(message))

    def __call__(self, connection: ServerConnection) -> None:
        self._connection = connection
        connections.add(self)

        logger.info("New connection received")

        for event in self.events():
            logger.info(event)
            match event:
                case EventMessage(kind=ClientEvent.LOGIN):
                    sleep(0.5)
                    player = Player(event.payload.get("nickname"))
                    players[self] = player
                    self.send_event(
                        EventMessage(kind=ServerEvent.LOGIN, payload={"nickname": player.nickname})
                    )
                case EventMessage(kind=ClientEvent.LOGOUT):
                    players.pop(self, None)

        logger.info("Connection closed")
        connections.remove(self)


def run_server(host: str, port: int) -> None:
    try:
        with serve(ConnectionHandler(), host=host, port=port) as server:
            logger.info(f"Serving at {host}:{port}")
            server.serve_forever()
    except KeyboardInterrupt:
        for connection in connections:
            logger.info(f"Closing connection with {connection.local_address}")
            connection.close()

        logger.info("Server shut down.")


if __name__ == "__main__":
    args = parser.parse_args()
    run_server(args.host, args.port)
