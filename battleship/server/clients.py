import abc
import asyncio

import redis.asyncio as redis

from battleship.server.pubsub import IncomingChannel, OutgoingChannel
from battleship.server.websocket import Client
from battleship.shared.models import Client as ClientModel


class ClientNotFound(Exception):
    pass


class ClientRepository(abc.ABC):
    def __init__(self, incoming_channel: IncomingChannel, outgoing_channel: OutgoingChannel):
        self._in_channel = incoming_channel
        self._out_channel = outgoing_channel

    @abc.abstractmethod
    async def add(self, client_id: str, nickname: str, guest: bool) -> Client:
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


class InMemoryClientRepository(ClientRepository):
    def __init__(
        self, incoming_channel: IncomingChannel, outgoing_channel: OutgoingChannel
    ) -> None:
        super().__init__(incoming_channel, outgoing_channel)
        self._clients: dict[str, Client] = {}

    async def add(self, user_id: str, nickname: str, guest: bool) -> Client:
        client = Client(user_id, nickname, guest, self._in_channel, self._out_channel)
        self._clients[client.id] = client
        return client

    async def get(self, client_id: str) -> Client:
        try:
            return self._clients[client_id]
        except KeyError:
            raise ClientNotFound(f"Client {client_id} doesn't exist.")

    async def list(self) -> list[Client]:
        return list(self._clients.values())

    async def delete(self, client_id: str) -> bool:
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


class RedisClientRepository(ClientRepository):
    key = "clients"
    namespace = key + ":"
    pattern = namespace + "*"

    def __init__(
        self,
        client: redis.Redis,
        incoming_channel: IncomingChannel,
        outgoing_channel: OutgoingChannel,
    ) -> None:
        super().__init__(incoming_channel, outgoing_channel)
        self._client = client

    def get_key(self, client_id: str) -> str:
        return f"{self.namespace}{client_id}"

    def get_client_id(self, key: str | bytes) -> str:
        if isinstance(key, bytes):
            key = key.decode()

        return key.removeprefix(self.namespace)

    async def add(self, client_id: str, nickname: str, guest: bool) -> Client:
        client = Client(client_id, nickname, guest, self._in_channel, self._out_channel)
        await self._save(client)
        return client

    async def get(self, client_id: str) -> Client:
        data = await self._client.get(self.get_key(client_id))

        if data is None:
            raise ClientNotFound(f"Client {client_id} not found.")

        model = ClientModel.from_raw(data)
        return Client(model.id, model.nickname, model.guest, self._in_channel, self._out_channel)

    async def list(self) -> list[Client]:
        keys = await self._client.keys(self.pattern)
        get_futures = [self.get(self.get_client_id(key)) for key in keys]
        return await asyncio.gather(*get_futures)

    async def delete(self, client_id: str) -> bool:
        return bool(await self._client.delete(self.get_key(client_id)))

    async def clear(self) -> int:
        keys: list[str] = await self._client.keys(self.pattern)
        count: int = await self._client.delete(*keys)
        return count

    async def _save(self, client: Client) -> bool:
        model = ClientModel(id=client.id, nickname=client.nickname, guest=client.guest)
        return bool(await self._client.set(self.get_key(client.id), model.to_json()))
