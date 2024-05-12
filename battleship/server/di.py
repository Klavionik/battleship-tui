from redis.asyncio import Redis
from rodi import Container

from battleship.server.auth import Auth0AuthManager, AuthManager
from battleship.server.bus import InMemoryMessageBus, MessageBus
from battleship.server.config import Config, get_config
from battleship.server.game import GameManager
from battleship.server.handlers import (
    ClientDisconnectedHandler,
    HandleServerGameEvent,
    PlayersIngameSubscriptionHandler,
    PlayersOnlineSubscriptionHandler,
    SessionUpdateHandler,
)
from battleship.server.repositories import (
    ClientRepository,
    RedisClientRepository,
    RedisSessionRepository,
    RedisStatisticsRepository,
    RedisSubscriptionsRepository,
    SessionRepository,
    StatisticsRepository,
    SubscriptionRepository,
)


def connect_event_handlers(services: Container) -> None:
    message_bus = services.resolve(MessageBus)
    message_bus.subscribe("entities.session", services.resolve(SessionUpdateHandler))
    message_bus.subscribe("entities.session.*", services.resolve(PlayersIngameSubscriptionHandler))
    message_bus.subscribe("entities.client", services.resolve(PlayersOnlineSubscriptionHandler))
    message_bus.subscribe("websocket", services.resolve(ClientDisconnectedHandler))
    message_bus.subscribe("games", services.resolve(HandleServerGameEvent))


def build_container() -> Container:
    container = Container()
    config = get_config()
    redis = Redis.from_url(str(config.REDIS_URL))
    container.add_instance(redis, Redis)
    message_bus = InMemoryMessageBus()

    container.add_singleton_by_factory(get_config, Config)
    container.add_instance(message_bus, MessageBus)
    container.add_singleton(SessionUpdateHandler)
    container.add_singleton(PlayersIngameSubscriptionHandler)
    container.add_singleton(PlayersOnlineSubscriptionHandler)
    container.add_singleton(ClientDisconnectedHandler)
    container.add_singleton(HandleServerGameEvent)
    container.add_singleton(AuthManager, Auth0AuthManager)
    container.add_singleton(SessionRepository, RedisSessionRepository)
    container.add_singleton(ClientRepository, RedisClientRepository)
    container.add_singleton(StatisticsRepository, RedisStatisticsRepository)
    container.add_singleton(SubscriptionRepository, RedisSubscriptionsRepository)
    container.add_singleton(GameManager)
    return container
