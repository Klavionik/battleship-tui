import argparse
import asyncio
import json
import signal
from asyncio import Task
from secrets import token_urlsafe
from typing import AsyncGenerator, cast

from loguru import logger
from websockets import WebSocketServerProtocol, serve  # type: ignore[attr-defined]

from battleship.shared.events import ClientEvent, EventMessage, ServerEvent

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="localhost")
parser.add_argument("--port", type=int, default=8000)


class Player:
    def __init__(self, nickname: str | None):
        self.nickname = nickname or "Guest"


connections: set["ConnectionHandler"] = set()
players: dict["ConnectionHandler", Player] = dict()
sessions_queue: dict[str, dict[str, str | bool]] = {}


class ConnectionHandler:
    def __init__(self) -> None:
        self._connection: WebSocketServerProtocol = None
        self._session_subscription: Task[None] | None = None

    @property
    def local_address(self) -> tuple[str, int]:
        return cast(tuple[str, int], self._connection.local_address)

    async def close(self) -> None:
        await self._connection.close()

    async def send_event(self, event: EventMessage) -> None:
        await self._connection.send(event.as_json())

    async def __aiter__(self) -> AsyncGenerator[EventMessage, None]:
        async for message in self._connection:
            yield EventMessage(**json.loads(message))

    async def __call__(self, connection: WebSocketServerProtocol) -> None:
        self._connection = connection
        connections.add(self)

        logger.info("New connection received")

        async for event in self:
            logger.info(event)
            match event:
                case EventMessage(kind=ClientEvent.LOGIN):
                    await asyncio.sleep(0.5)  # Artificial latency.
                    player = Player(event.payload.get("nickname"))
                    players[self] = player
                    await self.send_event(
                        EventMessage(kind=ServerEvent.LOGIN, payload={"nickname": player.nickname})
                    )
                case EventMessage(kind=ClientEvent.LOGOUT):
                    players.pop(self, None)
                case EventMessage(kind=ClientEvent.NEW_GAME):
                    session_id = token_urlsafe(4)
                    sessions_queue[session_id] = {
                        "name": event.payload["name"],
                        "roster": event.payload["roster"],
                        "firing_order": event.payload["firing_order"],
                        "salvo_mode": event.payload["salvo_mode"],
                    }
                case EventMessage(kind=ClientEvent.SESSIONS_SUBSCRIBE):

                    async def send_updates() -> None:
                        while True:
                            logger.info(f"Send sessions update: {len(sessions_queue)} sessions.")

                            await self.send_event(
                                EventMessage(
                                    kind=ServerEvent.SESSIONS_UPDATE,
                                    payload={"items": list(sessions_queue.items())},
                                )
                            )
                            await asyncio.sleep(2)

                    self._session_subscription = asyncio.create_task(send_updates())
                case EventMessage(kind=ClientEvent.SESSIONS_UNSUBSCRIBE):
                    if self._session_subscription is not None:
                        self._session_subscription.cancel()
                        self._session_subscription = None

        logger.info("Connection closed")
        connections.remove(self)


async def run_server(host: str, port: int) -> None:
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with serve(ConnectionHandler(), host=host, port=port):
        logger.info(f"Serving at {host}:{port}")
        await stop

    for connection in connections:
        logger.info(f"Closing connection with {connection.local_address}")
        await connection.close()

        logger.info("Server shut down.")


if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(run_server(args.host, args.port))
