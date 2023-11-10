import abc
import asyncio
from asyncio import Task
from typing import Any, Callable, Coroutine, TypeAlias

import redis.asyncio as redis
from loguru import logger

from battleship.shared.models import (
    Action,
    Session,
    SessionCreate,
    SessionID,
    make_session_id,
)

Listener: TypeAlias = Callable[[SessionID, Action], Coroutine]


class SessionNotFound(Exception):
    pass


class SessionRepository(abc.ABC):
    def __init__(self) -> None:
        self._listeners: dict[str, Listener] = {}
        self._notification_task: Task[None] | None = None

    @abc.abstractmethod
    async def add(self, host_id: str, data: SessionCreate) -> Session:
        pass

    @abc.abstractmethod
    async def get(self, session_id: str) -> Session:
        pass

    @abc.abstractmethod
    async def list(self) -> list[Session]:
        pass

    @abc.abstractmethod
    async def delete(self, session_id: str) -> bool:
        pass

    @abc.abstractmethod
    async def update(self, session_id: str, **kwargs: Any) -> Session:
        pass

    async def get_for_client(self, client_id: str) -> Session | None:
        try:
            [session] = [s for s in await self.list() if client_id in (s.host_id, s.guest_id)]
            return session
        except ValueError:
            return None

    def subscribe(self, callback_id: str, callback: Listener) -> None:
        self._listeners[callback_id] = callback

    def unsubscribe(self, callback_id: str) -> None:
        self._listeners.pop(callback_id, None)

    def _notify_listeners(self, session_id: str, action: Action) -> None:
        @logger.catch
        async def notify_task() -> None:
            logger.debug(f"Notify {len(self._listeners)} listeners.")

            for subscriber in self._listeners.values():
                await subscriber(session_id, action)

        @logger.catch
        def done_callback(_: asyncio.Future[None]) -> None:
            self._notification_task = None
            logger.trace("Notification task is cleaned up.")

        task = asyncio.create_task(notify_task())
        task.add_done_callback(done_callback)
        self._notification_task = task


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        super().__init__()
        self._sessions: dict[SessionID, Session] = {}

    async def add(self, host_id: str, data: SessionCreate) -> Session:
        session = Session(id=make_session_id(), host_id=host_id, **data.to_dict())
        self._sessions[session.id] = session
        self._notify_listeners(session.id, Action.ADD)
        return session

    async def get(self, session_id: str) -> Session:
        return self._sessions[session_id]

    async def list(self) -> list[Session]:
        return list(self._sessions.values())

    async def delete(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        self._notify_listeners(session_id, Action.REMOVE)
        return session is not None

    async def update(self, session_id: str, **kwargs: Any) -> Session:
        session = await self.get(session_id)
        updated_session = Session.from_dict({**session.to_dict(), **kwargs})
        self._notify_listeners(session_id, Action.START)
        return updated_session


class RedisSessionRepository(SessionRepository):
    def __init__(self, client: redis.Redis) -> None:
        super().__init__()
        self._client = client

    async def add(self, host_id: str, data: SessionCreate) -> Session:
        session = Session(id=make_session_id(), host_id=host_id, **data.to_dict())
        await self._client.set(session.id, session.to_json())
        self._notify_listeners(session.id, Action.ADD)
        return session

    async def get(self, session_id: str) -> Session:
        data = await self._client.get(session_id)

        if data is None:
            raise SessionNotFound(f"Session {session_id} not found.")

        return Session.from_raw(data)

    async def list(self) -> list[Session]:
        session_keys = await self._client.keys(pattern="session_*")
        sessions = await self._client.mget(session_keys)
        return list(map(Session.from_raw, sessions))

    async def delete(self, session_id: str) -> bool:
        deleted = await self._client.delete(session_id)
        self._notify_listeners(session_id, Action.REMOVE)
        return bool(deleted)

    async def update(self, session_id: str, **kwargs: Any) -> Session:
        session = await self.get(session_id)
        updated_session = Session.from_dict({**session.to_dict(), **kwargs})
        await self._client.set(session.id, updated_session.to_json())
        self._notify_listeners(session_id, Action.START)
        return updated_session
