import abc
import asyncio
from collections import deque
from typing import Any, AsyncIterator, Generic, TypeVar, cast

import pymitter  # type: ignore
from redis import asyncio as redis

from battleship.shared.events import AnyMessage, Message


class Broker(abc.ABC):
    @abc.abstractmethod
    async def publish(self, message: str, topic: str) -> None:
        pass

    @abc.abstractmethod
    def listen(self, topic: str) -> AsyncIterator[str]:
        pass


class InMemoryBroker(Broker):
    class pubsub:
        def __init__(self, emitter: pymitter.EventEmitter):
            self._ee = emitter
            self._messages: deque[str] = deque()
            self._topic: str | None = None

        def __enter__(self) -> "InMemoryBroker.pubsub":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            self._ee.off(self._topic, self._listener)

        def subscribe(self, topic: str) -> None:
            self._topic = topic
            self._ee.on(self._topic, self._listener)

        def _listener(self, message: str) -> None:
            self._messages.append(message)

        async def listen(self) -> AsyncIterator[str]:
            assert self._topic is not None

            while len(self._ee.listeners(self._topic)):
                try:
                    yield self._messages.popleft()
                except IndexError:
                    pass

                await asyncio.sleep(0.01)

    def __init__(self) -> None:
        self._emitter = pymitter.EventEmitter(wildcard=True)

    async def publish(self, message: str, topic: str) -> None:
        await self._emitter.emit_async(topic, message)

    async def listen(self, topic: str) -> AsyncIterator[str]:
        with self.pubsub(self._emitter) as pubsub:
            pubsub.subscribe(topic)

            async for message in pubsub.listen():
                yield message


class RedisBroker(Broker):
    IGNORED_MESSAGE_TYPES = {"psubscribe"}

    def __init__(self, client: redis.Redis):
        self._client = client

    async def listen(self, topic: str) -> AsyncIterator[str]:
        async with self._client.pubsub() as pubsub:
            await pubsub.psubscribe(topic)

            async for message in pubsub.listen():
                if message["type"] in self.IGNORED_MESSAGE_TYPES:
                    continue

                yield message["data"]

    async def publish(self, message: str, topic: str) -> None:
        await self._client.publish(topic, message)


T = TypeVar("T", bound=AnyMessage)


class Channel(Generic[T]):
    def __init__(self, prefix: str, broker: Broker):
        self._prefix = prefix
        self._broker = broker

    async def publish(self, message: T, topic: str | None = None) -> None:
        await self._broker.publish(message.to_json(), self._build_topic(topic))

    async def listen(self, topic: str | None = None) -> AsyncIterator[T]:
        async for message in self._broker.listen(self._build_topic(topic)):
            yield cast(T, Message.from_raw(message))

    def topic(self, topic: str) -> "Channel[T]":
        topic = self._prefix + "." + topic
        return Channel(prefix=topic, broker=self._broker)

    def _build_topic(self, topic: str | None = None) -> str:
        if topic:
            return self._prefix + "." + topic
        return self._prefix
