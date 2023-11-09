import abc

import redis.asyncio as redis

from battleship.server.pubsub import IncomingChannel, OutgoingChannel
from battleship.server.websocket import Client


class ClientNotFound(Exception):
    pass


class ClientRepository(abc.ABC):
    def __init__(self, incoming_channel: IncomingChannel, outgoing_channel: OutgoingChannel):
        self._in_channel = incoming_channel
        self._out_channel = outgoing_channel

    @abc.abstractmethod
    async def add(self, nickname: str) -> Client:
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


class InMemoryClientRepository(ClientRepository):
    def __init__(
        self, incoming_channel: IncomingChannel, outgoing_channel: OutgoingChannel
    ) -> None:
        super().__init__(incoming_channel, outgoing_channel)
        self._clients: dict[str, Client] = {}

    async def add(self, nickname: str) -> Client:
        client = Client(nickname, self._in_channel, self._out_channel)
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


class RedisClientRepository(ClientRepository):
    key = "clients"

    def __init__(
        self,
        client: redis.Redis,
        incoming_channel: IncomingChannel,
        outgoing_channel: OutgoingChannel,
    ) -> None:
        super().__init__(incoming_channel, outgoing_channel)
        self._client = client

    async def add(self, nickname: str) -> Client:
        client = Client(nickname, self._in_channel, self._out_channel)
        await self._client.sadd(self.key, nickname)  # type: ignore[misc]
        return client

    async def get(self, client_id: str) -> Client:
        is_connected = await self._client.sismember(self.key, client_id)  # type: ignore[misc]

        if not is_connected:
            raise ClientNotFound(f"Client {client_id} not found.")
        return Client(client_id, self._in_channel, self._out_channel)

    async def list(self) -> list[Client]:
        return list(await self._client.smembers(self.key))  # type: ignore[misc]

    async def delete(self, client_id: str) -> bool:
        return bool(await self._client.srem(self.key, client_id))  # type: ignore[misc]
