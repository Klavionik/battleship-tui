import asyncio

from battleship.server.bus import MessageBus
from battleship.server.repositories import ClientRepository, SessionRepository
from battleship.server.repositories.statistics import (
    StatisticsNotFound,
    StatisticsRepository,
)
from battleship.shared.events import GameEvent, Message, ServerGameEvent
from battleship.shared.models import PlayerCount, PlayerStatistics


async def count_players(
    client_repository: ClientRepository, session_repository: SessionRepository
) -> PlayerCount:
    players = await client_repository.count()
    sessions = await session_repository.list()
    started_sessions = [s for s in sessions if s.started]
    players_ingame = len(started_sessions) * 2
    return PlayerCount(total=players, ingame=players_ingame)


async def get_player_statistics(
    user_id: str, statistics_repository: StatisticsRepository
) -> PlayerStatistics:
    try:
        statistics = await statistics_repository.get(user_id)
    except StatisticsNotFound:
        statistics = await statistics_repository.create(user_id)

    return statistics


async def join_game_session(
    user_id: str,
    session_id: str,
    session_repository: SessionRepository,
    client_repository: ClientRepository,
    message_bus: MessageBus,
) -> None:
    session = await session_repository.get(session_id)
    players = await asyncio.gather(
        client_repository.get(session.host_id), client_repository.get(user_id)
    )
    host, guest = players
    await session_repository.update(session.id, guest_id=guest.id, started=True)

    await message_bus.emit(
        "games",
        Message(event=GameEvent(type=ServerGameEvent.START_GAME, session_id=session_id)),
    )
