from typing import Any, Callable, Coroutine, TypeAlias

from pyee.asyncio import AsyncIOEventEmitter

from battleship.shared.models import Action, Session, SessionID

ClientCount: TypeAlias = int
SessionCallback = Callable[[Session], Coroutine[Any, Any, Any]]
SessionIDCallback = Callable[[SessionID], Coroutine[Any, Any, Any]]
ClientCallback = Callable[[ClientCount], Coroutine[Any, Any, Any]]


class SessionSubscription:
    def __init__(self) -> None:
        self._ee = AsyncIOEventEmitter()

    def on_add(self, callback: SessionCallback) -> None:
        self._ee.add_listener(Action.ADD, callback)

    def on_remove(self, callback: SessionIDCallback) -> None:
        self._ee.add_listener(Action.REMOVE, callback)

    def on_start(self, callback: SessionIDCallback) -> None:
        self._ee.add_listener(Action.START, callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._ee.emit(event, *args, **kwargs)


class PlayerSubscription:
    def __init__(self) -> None:
        self._ee = AsyncIOEventEmitter()

    def on_online_changed(self, callback: ClientCallback) -> None:
        self._ee.add_listener("online_changed", callback)

    def on_ingame_changed(self, callback: ClientCallback) -> None:
        self._ee.add_listener("ingame_changed", callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._ee.emit(event, *args, **kwargs)
