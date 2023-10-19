import asyncio
from asyncio import Task
from typing import Callable, Coroutine, TypeAlias

from battleship.shared.sessions import Action, Session, SessionId

Listener: TypeAlias = Callable[[SessionId, Action], Coroutine]


class Sessions:
    def __init__(self) -> None:
        self._sessions: dict[SessionId, Session] = {}
        self._listeners: set[Listener] = set()
        self._notify_task: Task[None] | None = None

    def __iter__(self) -> list[Session]:
        return list(self._sessions.values())

    def __len__(self) -> int:
        return len(self)

    def add(self, session: Session) -> None:
        self._sessions[session.id] = session
        self._notify_listeners(session.id, Action.ADD)

    def get(self, session_id: str) -> Session:
        return self._sessions[session_id]

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._notify_listeners(session_id, Action.REMOVE)

    def subscribe(self, callback: Listener) -> None:
        self._listeners.add(callback)

    def unsubscribe(self, callback: Listener) -> None:
        self._listeners.discard(callback)

    def _notify_listeners(self, session_id: str, action: Action) -> None:
        async def notify_task() -> None:
            for subscriber in self._listeners:
                await subscriber(session_id, action)

        self._notify_task = asyncio.create_task(notify_task())
