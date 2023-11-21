import asyncio
from typing import Callable, Coroutine, TypeAlias

from loguru import logger

from battleship.shared.models import Action

EntityID: TypeAlias = str
Listener: TypeAlias = Callable[[EntityID, Action], Coroutine[None, None, None]]


class Observable:
    def __init__(self) -> None:
        self._listeners: dict[str, Listener] = {}
        self._notification_task: asyncio.Task[None] | None = None

    def subscribe(self, callback_id: str, callback: Listener) -> None:
        self._listeners[callback_id] = callback

    def unsubscribe(self, callback_id: str) -> None:
        self._listeners.pop(callback_id, None)

    def _notify_listeners(self, entity_id: EntityID, action: Action) -> None:
        @logger.catch
        async def notify_task() -> None:
            logger.debug(f"Notify {len(self._listeners)} listeners.")

            for subscriber in self._listeners.values():
                await subscriber(entity_id, action)

        @logger.catch
        def done_callback(_: asyncio.Future[None]) -> None:
            self._notification_task = None
            logger.trace("Notification task is cleaned up.")

        task = asyncio.create_task(notify_task())
        task.add_done_callback(done_callback)
        self._notification_task = task
