import asyncio
from typing import Any

from loguru import logger

from battleship.server import metrics
from battleship.server.bus import MessageBus
from battleship.server.game import Game
from battleship.server.repositories import (
    ClientRepository,
    SessionRepository,
    StatisticsRepository,
)
from battleship.server.repositories.subscriptions import SubscriptionRepository
from battleship.server.websocket import ClientMessage
from battleship.shared.events import (
    ClientDisconnectedEvent,
    EntityEvent,
    GameEvent,
    Message,
    NotificationEvent,
    ServerGameEvent,
    Subscription,
)
from battleship.shared.models import Action, GameSummary


class GameHandler:
    def __init__(
        self,
        sessions: SessionRepository,
        clients: ClientRepository,
        statistics: StatisticsRepository,
        message_bus: MessageBus,
    ):
        self._clients = clients
        self._sessions = sessions
        self._statistics = statistics
        self._message_bus = message_bus
        self._message_bus = message_bus
        self._games: dict[str, asyncio.Task[None]] = {}
        self._consumer = self._run_consumer()

    @logger.catch
    async def run_game(self, game: Game) -> None:
        try:
            metrics.games_now.inc({})
            summary = await game.play()
        finally:
            metrics.games_now.dec({})

        string_summary = summary.to_json()

        # Replace player nickname with their ID.
        string_summary = string_summary.replace(game.host.nickname, game.host.id).replace(
            game.guest.nickname, game.guest.id
        )

        summary = GameSummary.from_raw(string_summary)

        for _, player in game.clients.items():
            if not player.guest:
                await self._statistics.save(player.id, summary)

    async def start_new_game(self, session_id: str) -> None:
        session = await self._sessions.get(session_id)
        host = await self._clients.get(session.host_id)
        guest = await self._clients.get(session.guest_id)

        logger.debug(f"Start new game {host.nickname} vs. {guest.nickname}.")
        game = Game(host, guest, session, self._in_channel, self._out_channel)
        task = asyncio.create_task(self.run_game(game))

        def cleanup(_: asyncio.Task[None]) -> None:
            self._games.pop(session.id, None)
            asyncio.create_task(self._sessions.delete(session.id))
            logger.trace("Game {session_id} is cleaned up.", session_id=session.id)

        task.add_done_callback(cleanup)
        self._games[session.id] = task

    def _run_consumer(self) -> asyncio.Task[None]:
        @logger.catch
        async def consumer() -> None:
            try:
                async for msg in self._game_channel.listen():
                    await self.handle(msg)
            except asyncio.CancelledError:
                logger.debug("{conn} Stop message consumer.", conn=self)
                raise

        return asyncio.create_task(consumer())

    async def handle(self, msg: ClientMessage) -> None:
        event = msg.event

        match event:
            case GameEvent(type=ServerGameEvent.START_GAME):
                await self.start_new_game(event.payload["session_id"])
            case GameEvent(type=ServerGameEvent.CANCEL_GAME):
                self._games[event.payload["session_id"]].cancel()
            case _:
                logger.warning(f"Unknown message {event}.")


class SessionUpdateHandler:
    def __init__(
        self,
        message_bus: MessageBus,
        subscription_repository: SubscriptionRepository,
    ):
        self._message_bus = message_bus
        self._subscriptions = subscription_repository

    async def __call__(self, message: Message[EntityEvent]) -> None:
        logger.info(
            "{handler} called with message {message}",
            handler=self.__class__.__name__,
            message=message,
        )
        event = message.unwrap()

        payload: dict[str, Any] = dict(action=event.action)

        if event.action == Action.ADD:
            payload["session"] = event.payload

        if event.action in [Action.REMOVE, Action.START]:
            payload["session_id"] = event.entity_id

        await self._message_bus.emit(
            "notifications",
            Message(
                event=NotificationEvent(
                    subscription=Subscription.SESSIONS_UPDATE,
                    payload=payload,
                )
            ),
        )


class PlayersOnlineSubscriptionHandler:
    def __init__(
        self,
        client_repository: ClientRepository,
        message_bus: MessageBus,
    ):
        self._clients = client_repository
        self._message_bus = message_bus

    async def __call__(self, message: Message[EntityEvent]) -> None:
        logger.info(
            "{handler} called with message {message}",
            handler=self.__class__.__name__,
            message=message,
        )
        event = message.unwrap()

        if event.action not in (Action.ADD, Action.REMOVE):
            return

        payload = dict(type="online_changed", count=await self._clients.count())

        await self._message_bus.emit(
            "notifications",
            Message(
                event=NotificationEvent(
                    subscription=Subscription.PLAYERS_UPDATE,
                    payload=payload,
                )
            ),
        )


class PlayersIngameSubscriptionHandler:
    def __init__(
        self,
        session_repository: SessionRepository,
        message_bus: MessageBus,
    ):
        self._sessions = session_repository
        self._message_bus = message_bus

    async def __call__(self, message: Message[EntityEvent]) -> None:
        logger.info(
            "{handler} called with message {message}",
            handler=self.__class__.__name__,
            message=message,
        )
        event = message.unwrap()

        if event.action not in (Action.START, Action.REMOVE):
            return

        sessions = await self._sessions.list()
        started_sessions = [s for s in sessions if s.started]
        players_ingame = len(started_sessions) * 2
        payload = dict(type="ingame_changed", count=players_ingame)

        await self._message_bus.emit(
            "notifications",
            Message(
                event=NotificationEvent(
                    subscription=Subscription.PLAYERS_UPDATE,
                    payload=payload,
                )
            ),
        )


class ClientDisconnectedHandler:
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        session_repository: SessionRepository,
        client_repository: ClientRepository,
        message_bus: MessageBus,
    ):
        self._subscription_repository = subscription_repository
        self._session_repository = session_repository
        self._client_repository = client_repository
        self._message_bus = message_bus

    async def __call__(self, message: Message[ClientDisconnectedEvent]) -> None:
        logger.info(
            "{handler} called with message {message}",
            handler=self.__class__.__name__,
            message=message,
        )
        event = message.unwrap()

        await self._subscription_repository.delete_subscriber(
            Subscription.SESSIONS_UPDATE, event.client_id
        )
        await self._subscription_repository.delete_subscriber(
            Subscription.PLAYERS_UPDATE, event.client_id
        )

        current_session = await self._session_repository.get_for_client(event.client_id)

        if current_session:
            if current_session.started:
                await self._message_bus.emit(
                    "games",
                    Message(
                        event=GameEvent(
                            type=ServerGameEvent.CANCEL_GAME,
                            payload=dict(session_id=current_session.id),
                        )
                    ),
                )
            else:
                await self._session_repository.delete(current_session.id)

        await self._client_repository.delete(event.client_id)
