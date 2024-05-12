import abc
from collections.abc import Awaitable, Callable

from pymitter import EventEmitter  # type: ignore[import-untyped]

from battleship.shared.events import AnyMessage


class MessageBus(abc.ABC):
    @abc.abstractmethod
    async def emit(self, event: str, message: AnyMessage) -> None:
        pass

    @abc.abstractmethod
    def subscribe(self, event: str, func: Callable[..., Awaitable[None]]) -> None:
        pass

    @abc.abstractmethod
    def unsubscribe(self, event: str, func: Callable[..., Awaitable[None]]) -> None:
        pass


class InMemoryMessageBus(MessageBus):
    def __init__(self, emitter: EventEmitter | None = None):
        self._ee = emitter or EventEmitter()

    async def emit(self, event: str, message: AnyMessage) -> None:
        self._ee.emit_future(event, message)

    def subscribe(self, event: str, func: Callable[..., Awaitable[None]]) -> None:
        self._ee.on(event, func)

    def unsubscribe(self, event: str, func: Callable[..., Awaitable[None]]) -> None:
        self._ee.off(event, func)
