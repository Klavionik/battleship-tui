import asyncio
import json
from typing import Any, Callable, Optional, ParamSpec, Self, TypeVar

from pyee import EventEmitter
from pyee.asyncio import AsyncIOEventEmitter

# noinspection PyProtectedMember
from websockets.client import connect

from battleship.server import Event, GameEvent

P = ParamSpec("P")
T = TypeVar("T")


class Client:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._emitter: EventEmitter = AsyncIOEventEmitter()
        self.nickname: Optional[str] = None

    async def __aenter__(self) -> Self:
        self._ws = await connect(f"ws://{self._host}:{self._port}")
        self._worker_task = asyncio.create_task(self._worker())
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._worker_task.done()
        await self._ws.close()

    async def disconnect(self) -> None:
        await self._send(dict(kind=GameEvent.DISCONNECT))

    async def connect(self, nickname: str) -> None:
        await self._send(dict(kind=GameEvent.CONNECT, payload={"nickname": nickname}))
        self.nickname = nickname

    def on(self, event: GameEvent | str) -> Callable[[Callable[P, T]], Callable[P, T]]:
        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            self._emitter.add_listener(event, func)
            return func

        return decorator

    async def _worker(self) -> None:
        if self._ws is None:
            return

        async for message in self._ws:
            event = Event(**json.loads(message))
            self._emitter.emit(event.kind, event)

    async def _send(self, event: dict[str, Any]) -> None:
        if self._ws is None:
            return

        await self._ws.send(json.dumps(event))
