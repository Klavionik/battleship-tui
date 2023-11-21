import abc
from typing import Any

import redis.asyncio as redis

from battleship.server.repositories.observable import Observable
from battleship.shared.models import (
    Action,
    Session,
    SessionCreate,
    SessionID,
    make_session_id,
)


class SessionNotFound(Exception):
    pass


class SessionRepository(Observable, abc.ABC):
    def __init__(self) -> None:
        super().__init__()

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
