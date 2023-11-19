import sys

import redis.asyncio as redis
from blacksheep import Application
from blacksheep.server.authentication.jwt import JWTBearerAuthentication
from blacksheep.server.authorization import Policy
from guardpost.common import AuthenticatedRequirement
from loguru import logger

from battleship.server.auth import Auth0AuthManager, AuthManager
from battleship.server.clients import ClientRepository, RedisClientRepository
from battleship.server.config import Config, get_config
from battleship.server.handlers import GameHandler, SessionSubscriptionHandler
from battleship.server.pubsub import (
    IncomingChannel,
    IncomingRedisChannel,
    OutgoingChannel,
    OutgoingRedisChannel,
)
from battleship.server.routes import router
from battleship.server.sessions import RedisSessionRepository, SessionRepository
from battleship.server.statistics import RedisStatisticsRepository, StatisticsRepository


async def cleanup_clients(app: Application) -> None:
    client_repository = app.service_provider.get(ClientRepository)

    try:
        count = await client_repository.clear()
        logger.debug("Cleaned up {count} clients.", count=count)
    except Exception as exc:
        logger.exception(exc)
        raise


async def teardown_redis(app: Application) -> None:
    client = app.service_provider.get(redis.Redis)

    try:
        await client.aclose()
    except redis.RedisError:
        logger.exception("Cannot close Redis connection.")
        raise


def create_app() -> Application:
    config = get_config()
    logger.remove()
    logger.add(sys.stderr, level="TRACE" if config.TRACE else "DEBUG")
    broker = redis.Redis.from_url(str(config.BROKER_URL))

    app = Application(router=router)
    app.services.add_instance(config, Config)
    app.services.add_instance(broker, redis.Redis)
    app.services.add_singleton(AuthManager, Auth0AuthManager)
    app.services.add_singleton(SessionRepository, RedisSessionRepository)
    app.services.add_singleton(ClientRepository, RedisClientRepository)
    app.services.add_singleton(StatisticsRepository, RedisStatisticsRepository)
    app.services.add_singleton(IncomingChannel, IncomingRedisChannel)
    app.services.add_singleton(OutgoingChannel, OutgoingRedisChannel)
    app.services.add_singleton(SessionSubscriptionHandler)
    app.services.add_singleton(GameHandler)

    app.use_authentication().add(
        JWTBearerAuthentication(
            keys_url=config.auth0_jwks_url,
            valid_audiences=[config.AUTH0_CLIENT_ID],
            valid_issuers=[config.auth0_issuer],
        )
    )

    app.use_authorization().with_default_policy(
        Policy("authenticated", AuthenticatedRequirement()),
    )

    app.on_stop += cleanup_clients
    app.on_stop += teardown_redis
    return app
