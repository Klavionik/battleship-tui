import abc
import asyncio

import redis.asyncio as redis

from battleship.server.bus import MessageBus
from battleship.server.repositories.observable import Observable
from battleship.shared.models import Action, Client


class ClientNotFound(Exception):
    pass


class ClientAlreadyExists(Exception):
    pass


class ClientRepository(Observable, abc.ABC):
    entity = "client"

    def __init__(
        self,
        message_bus: MessageBus,
    ):
        super().__init__(message_bus)

    @abc.abstractmethod
    async def add(self, client_id: str, nickname: str, guest: bool, version: str) -> Client:
        pass

    @abc.abstractmethod
    async def get(self, client_id: str) -> Client:
        pass

    @abc.abstractmethod
    async def list(self) -> list[Client]:
        pass

    @abc.abstractmethod
    async def delete(self, client_id: str) -> bool:
        pass

    @abc.abstractmethod
    async def clear(self) -> int:
        pass

    @abc.abstractmethod
    async def count(self) -> int:
        pass

    @abc.abstractmethod
    async def exists(self, client_id: str) -> bool:
        pass


class InMemoryClientRepository(ClientRepository):
    def __init__(
        self,
        message_bus: MessageBus,
    ) -> None:
        super().__init__(message_bus)
        self._clients: dict[str, Client] = {}

    async def add(self, user_id: str, nickname: str, guest: bool, version: str) -> Client:
        client = Client(id=user_id, nickname=nickname, guest=guest, version=version)
        self._clients[client.id] = client
        await self.notify(client.id, Action.ADD)
        return client

    async def get(self, client_id: str) -> Client:
        try:
            return self._clients[client_id]
        except KeyError:
            raise ClientNotFound(f"Client {client_id} doesn't exist.")

    async def list(self) -> list[Client]:
        return list(self._clients.values())

    async def delete(self, client_id: str) -> bool:
        await self.notify(client_id, Action.REMOVE)
        return self._clients.pop(client_id, None) is not None

    async def clear(self) -> int:
        client_count = 0

        while True:
            try:
                self._clients.popitem()
                client_count += 1
            except KeyError:
                break

        return client_count

    async def count(self) -> int:
        return len(self._clients)

    async def exists(self, client_id: str) -> bool:
        return client_id in self._clients


class RedisClientRepository(ClientRepository):
    key = "clients"
    namespace = key + ":"
    pattern = namespace + "*"

    def __init__(
        self,
        client: redis.Redis,
        message_bus: MessageBus,
    ) -> None:
        super().__init__(message_bus)
        self._client = client
        self._lock = asyncio.Lock()

    def get_key(self, client_id: str) -> str:
        return f"{self.namespace}{client_id}"

    def get_client_id(self, key: str | bytes) -> str:
        if isinstance(key, bytes):
            key = key.decode()

        return key.removeprefix(self.namespace)

    async def add(self, client_id: str, nickname: str, guest: bool, version: str) -> Client:
        async with self._lock:
            if await self.exists(client_id):
                raise ClientAlreadyExists(f"Client {client_id=} already exists.")

            client = Client(id=client_id, nickname=nickname, guest=guest, version=version)
            await self._save(client)
            return client

    async def get(self, client_id: str) -> Client:
        data = await self._client.get(self.get_key(client_id))

        if data is None:
            raise ClientNotFound(f"Client {client_id} not found.")

        return Client.from_raw(data)

    async def list(self) -> list[Client]:
        keys = await self._client.keys(self.pattern)
        get_futures = [self.get(self.get_client_id(key)) for key in keys]
        return await asyncio.gather(*get_futures)

    async def delete(self, client_id: str) -> bool:
        result = bool(await self._client.delete(self.get_key(client_id)))
        await self.notify(client_id, Action.REMOVE)
        return result

    async def clear(self) -> int:
        keys: list[bytes] = await self._client.keys(self.pattern)

        if len(keys):
            count: int = await self._client.delete(*keys)
            return count
        return 0

    async def count(self) -> int:
        keys = await self._client.keys(self.pattern)
        return len(keys)

    async def exists(self, client_id: str) -> bool:
        return bool(await self._client.exists(self.get_key(client_id)))

    async def _save(self, client: Client) -> bool:
        model = Client(
            id=client.id, nickname=client.nickname, guest=client.guest, version=client.version
        )
        await self.notify(client.id, Action.ADD, payload=model.to_dict())
        return bool(await self._client.set(self.get_key(client.id), model.to_json()))
