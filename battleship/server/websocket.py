from typing import AsyncGenerator

from blacksheep import FromHeader, WebSocket, WebSocketDisconnectError

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


class Client:
    def __init__(
        self,
        client_id: str,
        connection: WebSocket,
        user: User,
    ) -> None:
        self._client_id = client_id
        self._connection = WebSocketWrapper(connection)
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

    async def __aiter__(self) -> AsyncGenerator[EventMessage, None]:
        async for message in self._connection:
            yield EventMessage.from_raw(message)
