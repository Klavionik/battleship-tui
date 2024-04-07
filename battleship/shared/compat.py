import asyncio
import sys
from types import TracebackType

if sys.version_info >= (3, 11):
    from asyncio import Timeout as _Timeout
    from enum import StrEnum
else:
    from async_timeout import Timeout as _Timeout
    from backports.strenum import StrEnum


__all__ = ["StrEnum", "Timeout", "async_timeout"]


class Timeout:
    """
    Adapts async_timeout.Timeout API to match asyncio.Timeout.
    """

    def __init__(self, deadline: float | None, loop: asyncio.AbstractEventLoop):
        if sys.version_info >= (3, 11):
            self._timeout = _Timeout(deadline)
        else:
            self._timeout = _Timeout(deadline, loop)

    def reschedule(self, delay: float | None) -> None:
        if hasattr(self._timeout, "reschedule"):
            self._timeout.reschedule(delay)
        else:
            self._timeout.update(delay)  # type: ignore

    async def __aenter__(self) -> "Timeout":
        await self._timeout.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            await self._timeout.__aexit__(exc_type, exc_val, exc_tb)
        except asyncio.TimeoutError:
            raise TimeoutError


def async_timeout(delay: float | None) -> Timeout:
    loop = asyncio.get_running_loop()

    if delay is not None:
        deadline = loop.time() + delay
    else:
        deadline = None
    return Timeout(deadline, loop)
