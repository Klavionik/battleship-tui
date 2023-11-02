import abc
from typing import AsyncGenerator

from blacksheep import FromHeader, WebSocket, WebSocketDisconnectError

from battleship.logger import server_logger as logger
from battleship.shared.events import EventMessage
from battleship.shared.models import User


class ClientID(FromHeader[str]):
    name = "X-Battleship-Client-ID"


class WebSocketWrapper:
    def __init__(self, socket: WebSocket):
        self.socket = socket

    async def __aiter__(self) -> AsyncGenerator[str, None]:
        while True:
            try:
                yield await self.socket.receive_text()
            except WebSocketDisconnectError:
                break


class EventHandler(abc.ABC):
    @abc.abstractmethod
    async def handle(self, client: "Client", event: EventMessage) -> None:
        pass


class Client:
    def __init__(
        self,
        client_id: str,
        connection: WebSocket,
        user: User,
    ) -> None:
        self._client_id = client_id
        self._connection = WebSocketWrapper(connection)
        self._handlers: dict[type[EventHandler], EventHandler] = {}
        self.user = user

    def __repr__(self) -> str:
        return f"<Client: {self.id} {self.local_address} {self.user.nickname}>"

    @property
    def id(self) -> str:
        return self._client_id

    @property
    def local_address(self) -> str:
        return self._connection.socket.client_ip

    async def close(self) -> None:
        await self._connection.socket.close()

    async def send_event(self, event: EventMessage) -> None:
        await self._connection.socket.send_text(event.to_json())

    async def listen(self) -> None:
        async for event in self:
            logger.info(event)
            for handler in self._handlers.values():
                await handler.handle(self, event)

    def add_handler(self, handler: EventHandler) -> None:
        handler_type = handler.__class__

        if handler_type in self._handlers:
            raise ValueError("Only 1 handler of any type is allowed.")

        self._handlers[handler.__class__] = handler

    def remove_handler(self, handler_type: type[EventHandler]) -> None:
        self._handlers.pop(handler_type, None)

    async def __aiter__(self) -> AsyncGenerator[EventMessage, None]:
        async for message in self._connection:
            yield EventMessage.from_raw(message)
