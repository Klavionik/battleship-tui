import sys
from typing import Any, Awaitable, Callable

import sentry_sdk
from blacksheep import Application, Request, Response
from blacksheep.server.authentication.jwt import JWTBearerAuthentication
from blacksheep.server.authorization import Policy
from guardpost.common import AuthenticatedRequirement
from loguru import logger
from redis.asyncio import Redis, RedisError
from rodi import Container
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from battleship import PACKAGE_NAME
from battleship.server import context
from battleship.server.config import Config
from battleship.server.di import build_container, connect_event_handlers
from battleship.server.metrics import (
    MetricsMiddleware,
    MetricsScraperAuthenticationHandler,
)
from battleship.server.repositories import ClientRepository
from battleship.server.routes import router


async def cleanup_clients(app: Application) -> None:
    client_repository = app.services.resolve(ClientRepository)

    try:
        count = await client_repository.clear()
        logger.debug("Cleaned up {count} clients.", count=count)
    except Exception as exc:
        logger.exception(exc)
        raise


async def teardown_redis(app: Application) -> None:
    client = app.services.resolve(Redis)

    try:
        await client.aclose()
    except RedisError:
        logger.exception("Cannot close Redis connection.")
        raise


def configure_sentry(app: Application, dsn: str, release: str) -> SentryAsgiMiddleware:
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=0.1,
        release=release,
    )

    return SentryAsgiMiddleware(app)


async def client_version_middleware(
    request: Request, handler: Callable[[Request], Awaitable[Response]]
) -> Response:
    version = (request.get_first_header(b"X-Client-Version") or b"0.0.0").decode()
    context.client_version.set(version)
    return await handler(request)


async def sentry_context_middleware(
    request: Request, handler: Callable[[Request], Awaitable[Response]]
) -> Response:
    sentry_sdk.set_context("client", {"version": context.client_version.get()})
    identity = request.identity

    if identity and identity.is_authenticated():
        sentry_sdk.set_user(
            {
                "id": identity.sub,
                "username": identity.get("nickname"),
                "email": identity.get("email"),
            }
        )

    return await handler(request)


def configure_logging(level: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=level)
    logger.enable(PACKAGE_NAME)


def create_app(container: Container | None = None) -> Any:
    services = container or build_container()
    connect_event_handlers(services)
    config = services.resolve(Config)
    configure_logging("TRACE" if config.TRACE else "DEBUG")

    app = Application(router=router, services=services)

    app.use_authentication().add(
        JWTBearerAuthentication(
            keys_url=config.auth0_jwks_url,
            valid_audiences=[config.AUTH0_CLIENT_ID],
            valid_issuers=[config.auth0_issuer],
        )
    )

    app.use_authentication().add(
        MetricsScraperAuthenticationHandler(scraper_secret=config.METRICS_SCRAPER_SECRET)
    )

    app.use_authorization().with_default_policy(
        Policy("authenticated", AuthenticatedRequirement()),
    )

    app.on_stop += cleanup_clients
    app.on_stop += teardown_redis

    app.middlewares.append(client_version_middleware)
    app.middlewares.append(sentry_context_middleware)
    app_router = app.router

    if config.SENTRY_DSN:
        app = configure_sentry(
            app,
            config.SENTRY_DSN,
            config.SERVER_VERSION,
        )  # type: ignore[assignment]

    if config.METRICS_SCRAPER_SECRET:
        app = MetricsMiddleware(app, router=app_router)  # type: ignore[assignment]

    return app
