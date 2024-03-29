import abc
from collections.abc import Awaitable, Callable
from typing import Any

import pyee.asyncio as pyee

from battleship.shared.events import AnyMessage


class MessageBus(abc.ABC):
    @abc.abstractmethod
    async def emit(self, event: str, message: AnyMessage) -> None:
        pass

    @abc.abstractmethod
    def subscribe(self, event: str, func: Callable[[...], Awaitable[None]]) -> Callable[[...], Any]:
        pass

    @abc.abstractmethod
    def unsubscribe(self, event: str, func: Callable[[...], Awaitable[None]]) -> None:
        pass


class PyeeMessageBus(MessageBus):
    def __init__(self, emitter: pyee.AsyncIOEventEmitter | None = None):
        self._ee = emitter or pyee.AsyncIOEventEmitter()

    async def emit(self, event: str, message: AnyMessage) -> None:
        self._ee.emit(event, message)

    def subscribe(self, event: str, func: Callable[[...], Awaitable[None]]) -> Callable[[...], Any]:
        return self._ee.on(event, func)

    def unsubscribe(self, event: str, func: Callable[[...], Awaitable[None]]) -> None:
        self._ee.remove_listener(event, func)
