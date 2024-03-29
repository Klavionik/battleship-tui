import abc
from typing import Any

import redis.asyncio as redis

from battleship.server.bus import MessageBus
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
    entity = "session"

    def __init__(self, message_bus: MessageBus) -> None:
        super().__init__(message_bus)

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
    def __init__(self, message_bus: MessageBus) -> None:
        super().__init__(message_bus)
        self._sessions: dict[SessionID, Session] = {}

    async def add(self, host_id: str, data: SessionCreate) -> Session:
        session = Session(id=make_session_id(), host_id=host_id, **data.to_dict())
        self._sessions[session.id] = session
        await self.notify(session.id, Action.ADD, payload=session.to_dict())
        return session

    async def get(self, session_id: str) -> Session:
        return self._sessions[session_id]

    async def list(self) -> list[Session]:
        return list(self._sessions.values())

    async def delete(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        await self.notify(session_id, Action.REMOVE)
        return session is not None

    async def update(self, session_id: str, **kwargs: Any) -> Session:
        session = await self.get(session_id)
        updated_session = Session.from_dict({**session.to_dict(), **kwargs})
        await self.notify(session_id, Action.START)
        return updated_session


class RedisSessionRepository(SessionRepository):
    key = "sessions"
    namespace = key + ":"
    pattern = namespace + "*"

    def __init__(self, client: redis.Redis, message_bus: MessageBus) -> None:
        super().__init__(message_bus)
        self._client = client

    def get_key(self, session_id: str) -> str:
        return f"{self.namespace}{session_id}"

    def get_session_id(self, key: str | bytes) -> str:
        if isinstance(key, bytes):
            key = key.decode()

        return key.removeprefix(self.namespace)

    async def add(self, host_id: str, data: SessionCreate) -> Session:
        session = Session(id=make_session_id(), host_id=host_id, **data.to_dict())
        await self._save(session)
        await self.notify(session.id, Action.ADD, payload=session.to_dict())
        return session

    async def get(self, session_id: str) -> Session:
        data = await self._client.get(self.get_key(session_id))

        if data is None:
            raise SessionNotFound(f"Session {session_id} not found.")

        return Session.from_raw(data)

    async def list(self) -> list[Session]:
        session_keys = await self._client.keys(pattern=self.pattern)
        sessions = await self._client.mget(session_keys)
        return list(map(Session.from_raw, sessions))

    async def delete(self, session_id: str) -> bool:
        deleted = await self._client.delete(self.get_key(session_id))
        await self.notify(session_id, Action.REMOVE)
        return bool(deleted)

    async def update(self, session_id: str, **kwargs: Any) -> Session:
        session = await self.get(session_id)
        updated_session = Session.from_dict({**session.to_dict(), **kwargs})
        await self._save(updated_session)
        await self.notify(session_id, Action.START)
        return updated_session

    async def _save(self, session: Session) -> None:
        await self._client.set(self.get_key(session.id), session.to_json())
