from typing import Any

from loguru import logger

from battleship.server.bus import MessageBus
from battleship.server.game import GameManager
from battleship.server.repositories import ClientRepository, SessionRepository
from battleship.server.repositories.subscriptions import SubscriptionRepository
from battleship.shared.events import (
    ClientDisconnectedEvent,
    EntityEvent,
    GameEvent,
    Message,
    NotificationEvent,
    ServerGameEvent,
    Subscription,
)
from battleship.shared.models import Action


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
                            type=ServerGameEvent.CANCEL_GAME, session_id=current_session.id
                        )
                    ),
                )
            else:
                await self._session_repository.delete(current_session.id)

        await self._client_repository.delete(event.client_id)


class HandleServerGameEvent:
    def __init__(self, game_manager: GameManager):
        self._game_manager = game_manager

    async def __call__(self, message: Message[GameEvent]) -> None:
        event = message.unwrap()
        assert event.session_id, "Session ID missing in a game event"

        match event.type:
            case ServerGameEvent.START_GAME:
                await self._game_manager.start_new_game(event.session_id)
            case ServerGameEvent.CANCEL_GAME:
                self._game_manager.cancel_game(event.session_id)
