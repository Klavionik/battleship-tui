import asyncio
from asyncio import Task
from typing import Callable, Coroutine, TypeAlias

from loguru import logger

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

    def add(self, host_id: str, data: SessionCreate) -> Session:
        session = Session(id=make_session_id(), host_id=host_id, **data.to_dict())
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

    def start(self, session_id: str, guest_id: str) -> None:
        session = self.get(session_id)
        session.started = True
        session.guest_id = guest_id
        self._notify_listeners(session_id, Action.START)

    def subscribe(self, nickname: str, callback: Listener) -> None:
        self._listeners[nickname] = callback

    def unsubscribe(self, nickname: str) -> None:
        self._listeners.pop(nickname, None)

    def _notify_listeners(self, session_id: str, action: Action) -> None:
        async def notify_task() -> None:
            logger.debug(f"Notify {len(self._listeners)} listeners.")

            for subscriber in self._listeners.values():
                await subscriber(session_id, action)

        self._notify_task = asyncio.create_task(notify_task())
