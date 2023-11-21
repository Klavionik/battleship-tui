import abc
import asyncio
import random

import redis.asyncio as redis
from loguru import logger

from battleship.shared.models import GameSummary, PlayerStatistics


class StatisticsNotFound(Exception):
    pass


class StatisticsRepository(abc.ABC):
    @abc.abstractmethod
    async def create(self, user_id: str) -> PlayerStatistics:
        pass

    @abc.abstractmethod
    async def get(self, user_id: str) -> PlayerStatistics:
        pass

    @abc.abstractmethod
    async def save(self, user_id: str, game_summary: GameSummary) -> bool:
        pass


class RedisStatisticsRepository(StatisticsRepository):
    key = "statistics"

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def get_key(self, user_id: str) -> str:
        return f"{self.key}:{user_id}"

    async def create(self, user_id: str) -> PlayerStatistics:
        statistics = PlayerStatistics(user_id=user_id)
        await self._client.set(self.get_key(user_id), statistics.to_json())
        return statistics

    async def get(self, user_id: str) -> PlayerStatistics:
        data = await self._client.get(self.get_key(user_id))

        if data is None:
            raise StatisticsNotFound

        return PlayerStatistics.from_raw(data)

    async def save(self, user_id: str, game_summary: GameSummary) -> bool:
        retries = 5
        ok = False

        async with self._client.pipeline(transaction=True) as pipe:
            while not ok and retries:
                ok = await self._save(user_id, game_summary, pipe)

                if not ok:
                    retries -= 1
                    await asyncio.sleep(random.random())

        return ok

    @logger.catch
    async def _save(
        self, user_id: str, game_summary: GameSummary, pipe: redis.client.Pipeline
    ) -> bool:
        key = self.get_key(user_id)

        await pipe.watch(key)
        await pipe.execute()

        data = await self._client.get(key)

        if data is None:
            statistics = PlayerStatistics(user_id=user_id)
        else:
            statistics = PlayerStatistics.from_raw(data)

        statistics.update_from_summary(game_summary)

        await pipe.set(key, statistics.to_json())
        [ok] = await pipe.execute()
        return bool(ok)
