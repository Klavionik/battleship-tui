import json
from asyncio import Event, Future, Task, create_task, get_running_loop
from functools import cache
from typing import Any, Callable, Coroutine, Optional

from pyee import AsyncIOEventEmitter

# noinspection PyProtectedMember
from websockets.client import WebSocketClientProtocol, connect

from battleship.shared.events import (
    ClientEvent,
    EventMessage,
    EventMessageData,
    ServerEvent,
)
from battleship.shared.sessions import Action, Session, SessionId


class SessionSubscription:
    def __init__(self) -> None:
        self._ee = AsyncIOEventEmitter()  # type: ignore[no-untyped-call]

    def on_add(self, callback: Callable[[Session], Coroutine[Any, Any, Any]]) -> None:
        self._ee.add_listener("add", callback)

    def on_remove(self, callback: Callable[[SessionId], Coroutine[Any, Any, Any]]) -> None:
        self._ee.add_listener("remove", callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._ee.emit(event, *args, **kwargs)


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
        self._emitter = AsyncIOEventEmitter()  # type: ignore[no-untyped-call]
        self._publish_task: Task[None] | None = None
        self.logged_in = False
        self.nickname = ""

    async def connect(self) -> None:
        self._ws = await connect(f"ws://{self._host}:{self._port}")
        self._publish_task = create_task(self._publish_events())

    async def disconnect(self) -> None:
        if self._publish_task:
            self._publish_task.cancel()

        if self._ws:
            await self._ws.close()

    async def logout(self) -> None:
        if self.logged_in:
            await self._send(dict(kind=ClientEvent.LOGOUT))
            self.logged_in = False
            self.nickname = ""

    async def login(self, nickname: str | None = None) -> str:
        await self._send(dict(kind=ClientEvent.LOGIN, payload={"nickname": nickname}))
        signal = Event()

        async def _await_login_confirmed(payload: dict[str, str]) -> None:
            self.logged_in = True
            self.nickname = payload["nickname"]
            signal.set()

        self._emitter.once(ServerEvent.LOGIN, _await_login_confirmed)
        await signal.wait()
        return self.nickname

    async def announce_new_game(
        self,
        name: str,
        roster: str,
        firing_order: str,
        salvo_mode: bool,
    ) -> SessionId:
        payload = dict(name=name, roster=roster, firing_order=firing_order, salvo_mode=salvo_mode)
        await self._send(dict(kind=ClientEvent.NEW_GAME, payload=payload))
        future: Future[str] = get_running_loop().create_future()

        async def _await_session_created(payload_: dict[str, str]) -> None:
            future.set_result(payload_["session_id"])

        self._emitter.once(ServerEvent.NEW_GAME, _await_session_created)

        await future
        return future.result()

    async def abort_game(self, session_id: SessionId) -> None:
        payload = dict(session_id=session_id)
        await self._send(dict(kind=ClientEvent.ABORT_GAME, payload=payload))

    async def sessions_subscribe(self) -> SessionSubscription:
        subscription = SessionSubscription()

        async def publish_update(payload: dict) -> None:  # type: ignore[type-arg]
            action = payload["action"].lower()
            kwargs: dict[str, str | Session] = {}

            if action == Action.ADD.lower():
                kwargs.update(session=Session(**payload["session"]))

            if action == Action.REMOVE.lower():
                kwargs.update(session_id=payload["session_id"])

            subscription.emit(action, **kwargs)

        self._emitter.add_listener(ServerEvent.SESSIONS_UPDATE, publish_update)
        await self._send(dict(kind=ClientEvent.SESSIONS_SUBSCRIBE))
        return subscription

    async def sessions_unsubscribe(self) -> None:
        await self._send(dict(kind=ClientEvent.SESSIONS_UNSUBSCRIBE))

    async def _publish_events(self) -> None:
        if self._ws is None:
            raise RuntimeError("Cannot receive messages, no connection.")

        async for message in self._ws:
            event = EventMessage.from_raw(message)
            self._emitter.emit(event.kind, event.payload)

    async def _send(self, msg: EventMessageData) -> None:
        if self._ws is None:
            raise RuntimeError("Cannot send a message, no connection.")

        await self._ws.send(json.dumps(msg))


@cache
def get_client(host: str = "localhost", port: int = 8000) -> RealtimeClient:
    return RealtimeClient(host, port)
