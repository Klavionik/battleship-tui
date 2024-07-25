from collections.abc import AsyncIterator
from typing import Any

import websockets
from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_delay,
    wait_fixed,
)


class ConnectionRejected(RuntimeError):
    pass


class ConnectionImpossible(RuntimeError):
    pass


def not_status_code_403(exc: BaseException) -> bool:
    """
    A custom retry decision function.

    Do not retry if the exception is a websockets.InvalidStatusCode
    and the status code is 403. This means that the server has
    rejected the connection.

    In any other case, retry.
    """
    return not (isinstance(exc, websockets.InvalidStatusCode) and exc.status_code == 403)


async def connect(
    url: str, extra_headers: dict[str, Any], timeout: float
) -> AsyncIterator[websockets.WebSocketClientProtocol]:
    while True:
        retrier = AsyncRetrying(
            stop=stop_after_delay(timeout),
            wait=wait_fixed(2),
            retry=retry_if_exception(not_status_code_403),
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
            # Connection is not retried only if the server has rejected the connection.
            logger.warning("Connection rejected, another client is already connected.")
            raise ConnectionRejected
