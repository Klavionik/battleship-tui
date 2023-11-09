import abc
from typing import AsyncIterator, Callable, Iterable, TypeAlias

import redis.asyncio as redis
from loguru import logger

from battleship.shared.events import EventMessage

Callback: TypeAlias = Callable[[str], None]


class Channel(abc.ABC):
    @abc.abstractmethod
    async def publish(self, client_id: str | Iterable[str], event: EventMessage) -> None:
        pass

    @abc.abstractmethod
    def listen(
        self, client_id: str | Iterable[str] | None = None
    ) -> AsyncIterator[tuple[str | None, EventMessage]]:
        pass


class IncomingChannel(Channel, abc.ABC):
    pass


class OutgoingChannel(Channel, abc.ABC):
    pass


class RedisChannel(Channel):
    IGNORED_MESSAGE_TYPES = {"psubscribe"}

    def __init__(self, topic: str, client: redis.Redis):
        self.topic = topic
        self._client = client

    async def publish(self, client_id: str | Iterable[str], event: EventMessage) -> None:
        topic = self.build_topic(client_id)
        await self._client.publish(topic, event.to_json())

    async def listen(
        self, client_id: str | Iterable[str] | None = None
    ) -> AsyncIterator[tuple[str | None, EventMessage]]:
        topic = self.build_topic(client_id)

        async with self._client.pubsub() as pubsub:
            await pubsub.psubscribe(topic)

            async for message in pubsub.listen():
                if message["type"] in self.IGNORED_MESSAGE_TYPES:
                    continue

                logger.debug("New message from broker {message}", message=message)

                if client_id is None:
                    yield None, EventMessage.from_raw(message["data"])
                    continue

                target = message["channel"].split(b".", maxsplit=1)[1]

                yield target, EventMessage.from_raw(message["data"])

    def build_topic(self, client_id: str | Iterable[str] | None = None) -> str:
        if isinstance(client_id, str):
            return self.topic.replace("*", client_id)
        elif isinstance(client_id, Iterable):
            return " ".join(self.topic.replace("*", client) for client in client_id)

        return self.topic


class IncomingRedisChannel(RedisChannel, IncomingChannel):
    def __init__(self, client: redis.Redis):
        super().__init__("in.*", client)


class OutgoingRedisChannel(RedisChannel, OutgoingChannel):
    def __init__(self, client: redis.Redis):
        super().__init__("out.*", client)
