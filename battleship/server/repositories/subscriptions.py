import abc
from collections import defaultdict

import redis.asyncio as redis

from battleship.shared.events import Subscription


class SubscriptionNotFound(Exception):
    pass


class SubscriptionRepository(abc.ABC):
    @abc.abstractmethod
    async def add_subscriber(self, subscription: Subscription, subscriber: str) -> None:
        pass

    @abc.abstractmethod
    async def get_subscribers(self, subscription: Subscription) -> set[str]:
        pass

    @abc.abstractmethod
    async def delete_subscriber(self, subscription: Subscription, subscriber: str) -> None:
        pass

    @abc.abstractmethod
    async def clear(self) -> None:
        pass


class InMemorySubscriptionRepository(SubscriptionRepository):
    def __init__(self, subscriptions: dict[str, set[str]] | None = None) -> None:
        self._subscriptions: dict[str, set[str]] = defaultdict(set)

        if subscriptions:
            self._subscriptions.update(subscriptions)

    async def add_subscriber(self, subscription: Subscription, subscriber: str) -> None:
        self._subscriptions[subscription].add(subscriber)

    async def get_subscribers(self, subscription: Subscription) -> set[str]:
        return self._subscriptions[subscription]

    async def delete_subscriber(self, subscription: Subscription, subscriber: str) -> None:
        try:
            self._subscriptions[subscription].remove(subscriber)
        except KeyError:
            pass

    async def clear(self) -> None:
        self._subscriptions.clear()


class RedisSubscriptionsRepository(SubscriptionRepository):
    key = "subscriptions"
    namespace = key + ":"
    pattern = namespace + "*"

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def get_key(self, subscription: Subscription) -> str:
        return f"{self.key}:{subscription}"

    async def get_subscribers(self, subscription: Subscription) -> set[str]:
        subscribers = await self._client.smembers(self.get_key(subscription))  # type: ignore[misc]
        return {subscriber.decode() for subscriber in subscribers}

    async def add_subscriber(self, subscription: Subscription, subscriber: str) -> None:
        await self._client.sadd(self.get_key(subscription), subscriber)  # type: ignore[misc]

    async def delete_subscriber(self, subscription: Subscription, subscriber: str) -> None:
        await self._client.srem(self.get_key(subscription), subscriber)  # type: ignore[misc]

    async def clear(self) -> None:
        keys: list[bytes] = await self._client.keys(self.pattern)

        if len(keys):
            await self._client.delete(*keys)
