import asyncio
from asyncio import Task
from typing import Callable, Coroutine, TypeAlias

from battleship.logger import server_logger as logger
from battleship.shared.models import (
    Action,
    Session,
    SessionCreate,
    SessionID,
    make_session_id,
)

Listener: TypeAlias = Callable[[SessionID, Action], Coroutine]


class Sessions:
    def __init__(self) -> None:
        self._sessions: dict[SessionID, Session] = {}
        self._listeners: dict[str, Listener] = {}
        self._notify_task: Task[None] | None = None

    def add(self, data: SessionCreate) -> Session:
        session = Session(id=make_session_id(), **data.to_dict())
        self._sessions[session.id] = session
        self._notify_listeners(session.id, Action.ADD)
        return session

    def get(self, session_id: str) -> Session:
        return self._sessions[session_id]

    def list(self) -> list[Session]:
        return list(self._sessions.values())

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._notify_listeners(session_id, Action.REMOVE)

    def start(self, session_id: str) -> None:
        session = self.get(session_id)
        session.started = True
        self._notify_listeners(session_id, Action.START)

    def subscribe(self, client_id: str, callback: Listener) -> None:
        self._listeners[client_id] = callback

    def unsubscribe(self, client_id: str) -> None:
        self._listeners.pop(client_id, None)

    def _notify_listeners(self, session_id: str, action: Action) -> None:
        async def notify_task() -> None:
            logger.debug(f"Notify {len(self._listeners)} listeners.")

            for subscriber in self._listeners.values():
                await subscriber(session_id, action)

        self._notify_task = asyncio.create_task(notify_task())
