import json
from collections.abc import AsyncGenerator
from functools import cache
from typing import Optional

# noinspection PyProtectedMember
from websockets.client import WebSocketClientProtocol, connect

from battleship.shared.events import (
    ClientEvent,
    EventMessage,
    EventMessageData,
    ServerEvent,
)


class RealtimeClient:
    """
    Wraps WebSockets connection and provides a convenient interface
    for sending client events to the realtime server and receiving
    server events via `async for`.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._ws: Optional[WebSocketClientProtocol] = None

        self.logged_in = False
        self.nickname = ""

    async def connect(self) -> None:
        self._ws = await connect(f"ws://{self._host}:{self._port}")

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()

    async def logout(self) -> None:
        if self.logged_in:
            await self._send(dict(kind=ClientEvent.LOGOUT))
            self.logged_in = False
            self.nickname = ""

    async def login(self, nickname: str | None = None) -> str:
        await self._send(dict(kind=ClientEvent.LOGIN, payload={"nickname": nickname}))
        await self._await_login_confirmed()
        return self.nickname

    async def _await_login_confirmed(self) -> None:
        async for event in self:
            if event.kind == ServerEvent.LOGIN:
                self.logged_in = True
                self.nickname = event.payload["nickname"]
                break

    async def __aiter__(self) -> AsyncGenerator[EventMessage, None]:
        if self._ws is None:
            raise RuntimeError("Cannot receive messages, no connection.")

        async for message in self._ws:
            yield EventMessage.from_raw(message)

    async def _send(self, msg: EventMessageData) -> None:
        if self._ws is None:
            raise RuntimeError("Cannot send a message, no connection.")

        await self._ws.send(json.dumps(msg))


@cache
def get_client(host: str = "localhost", port: int = 8000) -> RealtimeClient:
    return RealtimeClient(host, port)
