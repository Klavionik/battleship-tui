import asyncio

import pytest

from battleship.server.pubsub import Broker, Channel, InMemoryBroker
from battleship.shared.events import GameEvent, Message, ServerGameEvent


class FakeConsumer:
    def __init__(self, topic: str | None, producer: Broker | Channel):
        if not isinstance(topic, str) and isinstance(producer, Broker):
            raise TypeError("Broker topic should be a str.")

        self.topic = topic
        self.producer = producer
        self.messages = []
        self.task = None

    async def start(self):
        self.task = asyncio.create_task(self.consume())
        await asyncio.sleep(0.01)

    async def stop(self):
        assert self.task, "You should call start() before stop()"
        await asyncio.sleep(0.01)
        self.task.cancel()

    async def consume(self):
        async for message in self.producer.listen(topic=self.topic):
            self.messages.append(message)

    def __mul__(self, count: int) -> tuple["FakeConsumer", ...]:
        assert isinstance(count, int)
        return tuple(FakeConsumer(self.topic, self.producer) for _ in range(count))


@pytest.fixture
def inmemory_broker() -> InMemoryBroker:
    return InMemoryBroker()


async def test_broker_one_consumer(inmemory_broker):
    consumer = FakeConsumer("messages", inmemory_broker)
    await consumer.start()

    await inmemory_broker.publish("message", topic="messages")
    await consumer.stop()

    assert len(consumer.messages) == 1
    assert consumer.messages == ["message"]


async def test_broker_two_consumers(inmemory_broker):
    consumer, consumer_1 = FakeConsumer("messages", inmemory_broker) * 2
    await consumer.start()
    await consumer_1.start()

    await inmemory_broker.publish("message", topic="messages")

    await consumer.stop()
    await consumer_1.stop()

    assert len(consumer.messages) == 1
    assert consumer.messages == ["message"]
    assert len(consumer_1.messages) == 1
    assert consumer_1.messages == ["message"]


async def test_broker_publish_to_subtopic(inmemory_broker):
    consumer = FakeConsumer("messages", inmemory_broker)
    consumer_wildcard = FakeConsumer("messages.*", inmemory_broker)

    await consumer.start()
    await consumer_wildcard.start()

    await inmemory_broker.publish("update", topic="messages.update")

    await consumer.stop()
    await consumer_wildcard.stop()

    assert len(consumer.messages) == 0
    assert len(consumer_wildcard.messages) == 1

    assert consumer_wildcard.messages == ["update"]


async def test_channel(inmemory_broker):
    channel = Channel("messages", inmemory_broker)
    consumer = FakeConsumer(None, channel)
    await consumer.start()

    msg = Message(event=GameEvent(type=ServerGameEvent.START_GAME))
    await channel.publish(msg)

    await consumer.stop()
    assert len(consumer.messages) == 1
    assert consumer.messages == [msg]


async def test_channel_two_consumers(inmemory_broker):
    channel = Channel("messages", inmemory_broker)
    consumer, consumer_1 = FakeConsumer(None, channel) * 2
    await consumer.start()
    await consumer_1.start()

    msg = Message(event=GameEvent(type=ServerGameEvent.START_GAME))
    await channel.publish(msg)

    await consumer.stop()
    await consumer_1.stop()
    assert len(consumer.messages) == 1
    assert len(consumer_1.messages) == 1
    assert consumer.messages == [msg]
    assert consumer_1.messages == [msg]


async def test_channel_publish_to_subtopic(inmemory_broker):
    channel = Channel("messages", inmemory_broker)
    consumer = FakeConsumer(None, channel)
    consumer_wildcard = FakeConsumer("*", channel)

    await consumer.start()
    await consumer_wildcard.start()

    msg = Message(event=GameEvent(type=ServerGameEvent.START_GAME))
    await channel.publish(msg, topic="update")

    await consumer.stop()
    await consumer_wildcard.stop()

    assert len(consumer.messages) == 0
    assert len(consumer_wildcard.messages) == 1
    assert consumer_wildcard.messages == [msg]


async def test_channel_subtopic(inmemory_broker):
    channel = Channel("messages", inmemory_broker)
    subtopic = channel.topic("client_123")
    consumer = FakeConsumer(None, channel)
    consumer_subtopic = FakeConsumer(None, subtopic)
    await consumer.start()
    await consumer_subtopic.start()

    msg = Message(event=GameEvent(type=ServerGameEvent.START_GAME))
    await subtopic.publish(msg)

    await consumer.stop()
    await consumer_subtopic.stop()
    assert len(consumer.messages) == 0
    assert len(consumer_subtopic.messages) == 1
    assert consumer_subtopic.messages == [msg]
