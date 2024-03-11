import asyncio
from typing import Any

from loguru import logger

from battleship.server import metrics
from battleship.server.game import Game
from battleship.server.pubsub import Broker, Channel
from battleship.server.repositories import (
    ClientRepository,
    EntityChannel,
    SessionRepository,
    StatisticsRepository,
)
from battleship.server.repositories.subscriptions import (
    Subscription,
    SubscriptionRepository,
)
from battleship.server.websocket import ClientInChannel, ClientMessage, ClientOutChannel
from battleship.shared.events import (
    EntityEvent,
    GameEvent,
    Message,
    Notification,
    NotificationEvent,
    ServerGameEvent,
)
from battleship.shared.models import Action, GameSummary


class GameChannel(Channel[Message[GameEvent]]):
    def __init__(self, broker: Broker):
        super().__init__("games", broker)


class GameHandler:
    def __init__(
        self,
        sessions: SessionRepository,
        clients: ClientRepository,
        statistics: StatisticsRepository,
        in_channel: ClientInChannel,
        out_channel: ClientOutChannel,
        game_channel: GameChannel,
    ):
        self._clients = clients
        self._sessions = sessions
        self._statistics = statistics
        self._in_channel = in_channel
        self._out_channel = out_channel
        self._game_channel = game_channel
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
        string_summary = string_summary.replace(game.host.nickname, game.host.user_id).replace(
            game.guest.nickname, game.guest.user_id
        )

        summary = GameSummary.from_raw(string_summary)

        for _, player in game.clients.items():
            if not player.guest:
                await self._statistics.save(player.user_id, summary)

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


class SessionSubscriptionHandler:
    def __init__(
        self,
        client_out_channel: ClientOutChannel,
        entity_channel: EntityChannel,
        subscription_repository: SubscriptionRepository,
    ):
        self._client_out_channel = client_out_channel
        self._entity_channel = entity_channel
        self._consumer = self._run_consumer()
        self._subscriptions = subscription_repository

    async def notify(self, event: EntityEvent) -> None:
        payload: dict[str, Any] = dict(action=event.action)

        if event.action == Action.ADD:
            payload["session"] = event.payload

        if event.action in [Action.REMOVE, Action.START]:
            payload["session_id"] = event.payload["id"]

        for subscriber in await self._subscriptions.get_subscribers(Subscription.SESSIONS_UPDATE):
            await self._client_out_channel.publish(
                Message(
                    event=NotificationEvent(
                        notification=Notification.SESSIONS_UPDATE,
                        payload=payload,
                    )
                ),
                subscriber,
            )

    def _run_consumer(self) -> asyncio.Task[None]:
        @logger.catch
        async def consumer() -> None:
            try:
                async for msg in self._entity_channel.listen("session.*"):
                    event = msg.unwrap()
                    await self.notify(event)
            except asyncio.CancelledError:
                logger.debug("{conn} Stop message consumer.", conn=self)
                raise

        return asyncio.create_task(consumer())


class PlayersOnlineSubscriptionHandler:
    def __init__(
        self,
        client_out_channel: ClientOutChannel,
        client_repository: ClientRepository,
        entity_channel: EntityChannel,
        subscription_repository: SubscriptionRepository,
    ):
        self._client_out_channel = client_out_channel
        self._clients = client_repository
        self._entity_channel = entity_channel
        self._subscriptions = subscription_repository

    async def notify(self, event: EntityEvent) -> None:
        if event.action not in (Action.ADD, Action.REMOVE):
            return

        payload = dict(event="online_changed", count=await self._clients.count())

        for subscriber in await self._subscriptions.get_subscribers(Subscription.PLAYERS_UPDATE):
            await self._client_out_channel.publish(
                Message(
                    event=NotificationEvent(
                        notification=Notification.PLAYERS_UPDATE,
                        payload=payload,
                    )
                ),
                subscriber,
            )

    def _run_consumer(self) -> asyncio.Task[None]:
        @logger.catch
        async def consumer() -> None:
            try:
                async for msg in self._entity_channel.listen("client"):
                    event = msg.unwrap()
                    await self.notify(event)
            except asyncio.CancelledError:
                logger.debug("{conn} Stop message consumer.", conn=self)
                raise

        return asyncio.create_task(consumer())


class PlayersIngameSubscriptionHandler:
    def __init__(
        self,
        client_out_channel: ClientOutChannel,
        session_repository: SessionRepository,
        entity_channel: EntityChannel,
        subscription_repository: SubscriptionRepository,
    ):
        self._client_out_channel = client_out_channel
        self._sessions = session_repository
        self._entity_channel = entity_channel
        self._subscriptions = subscription_repository

    async def notify(self, event: EntityEvent) -> None:
        if event.action not in (Action.START, Action.REMOVE):
            return

        sessions = await self._sessions.list()
        started_sessions = [s for s in sessions if s.started]
        players_ingame = len(started_sessions) * 2
        payload = dict(event="ingame_changed", count=players_ingame)

        for subscriber in await self._subscriptions.get_subscribers(Subscription.PLAYERS_UPDATE):
            await self._client_out_channel.publish(
                Message(
                    event=NotificationEvent(
                        notification=Notification.PLAYERS_UPDATE,
                        payload=payload,
                    )
                ),
                subscriber,
            )

    def _run_consumer(self) -> asyncio.Task[None]:
        @logger.catch
        async def consumer() -> None:
            try:
                async for msg in self._entity_channel.listen("session.*"):
                    event = msg.unwrap()
                    await self.notify(event)
            except asyncio.CancelledError:
                logger.debug("{conn} Stop message consumer.", conn=self)
                raise

        return asyncio.create_task(consumer())
