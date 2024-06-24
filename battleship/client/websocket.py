from collections.abc import AsyncIterator
from typing import Any

import websockets
from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_not_exception_type,
    stop_after_delay,
    wait_exponential,
)


class ConnectionRejected(RuntimeError):
    pass


class ConnectionImpossible(RuntimeError):
    pass


async def connect(
    url: str, extra_headers: dict[str, Any], timeout: float
) -> AsyncIterator[websockets.WebSocketClientProtocol]:
    while True:
        retrier = AsyncRetrying(
            stop=stop_after_delay(timeout),
            wait=wait_exponential(min=2, max=5),
            retry=retry_if_not_exception_type(websockets.InvalidStatusCode),
        )

        try:
            async for attempt in retrier:
                logger.warning(
                    "Connection: attempt {number}.", number=attempt.retry_state.attempt_number
                )

                with attempt:
                    connection = await websockets.connect(
                        url,
                        extra_headers=extra_headers,
                        close_timeout=1,
                        ping_timeout=2,
                        ping_interval=5,
                    )

            yield connection
        except RetryError:
            logger.warning("Cannot connect after {idle} s.", idle=retrier.statistics["idle_for"])
            raise ConnectionImpossible
        except websockets.InvalidStatusCode:
            logger.warning("Connection rejected, another client is already connected.")
            raise ConnectionRejected
