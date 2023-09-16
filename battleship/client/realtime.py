import asyncio
import json
from typing import Callable, Optional, ParamSpec, TypeVar

from pyee import EventEmitter
from pyee.asyncio import AsyncIOEventEmitter

# noinspection PyProtectedMember
from websockets.client import WebSocketClientProtocol, connect

from battleship.shared.events import ClientEvent, Event, EventMessage, EventMessageData

P = ParamSpec("P")
T = TypeVar("T")


class RealtimeClient:
    """
    Wraps WebSockets connection and provides a convenient interface
    for sending client events to the realtime server. Receives
    server events and publishes them via an event emitter.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._emitter: EventEmitter = AsyncIOEventEmitter()
        self._ws: Optional[WebSocketClientProtocol] = None
        self._worker: Optional[asyncio.Task[None]] = None

    async def connect(self) -> None:
        self._ws = await connect(f"ws://{self._host}:{self._port}")
        self._worker = asyncio.create_task(self._run_worker())

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()

        if self._worker:
            self._worker.done()

    async def logout(self) -> None:
        await self._send(dict(kind=ClientEvent.LOGOUT))

    async def login(self, nickname: str) -> None:
        await self._send(dict(kind=ClientEvent.LOGIN, payload={"nickname": nickname}))

    def on(self, event: Event | str) -> Callable[[Callable[P, T]], Callable[P, T]]:
        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            self._emitter.add_listener(event, func)
            return func

        return decorator

    async def _run_worker(self) -> None:
        if self._ws is None:
            raise RuntimeError("Cannot run worker, no connection.")

        async for message in self._ws:
            msg = EventMessage.from_raw(message)
            self._emitter.emit(msg.kind, msg.payload)

    async def _send(self, msg: EventMessageData) -> None:
        if self._ws is None:
            raise RuntimeError("Cannot send a message, no connection.")

        await self._ws.send(json.dumps(msg))
