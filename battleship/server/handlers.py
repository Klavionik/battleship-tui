import asyncio
from typing import Any

from loguru import logger

from battleship.server.game import Game
from battleship.server.pubsub import IncomingChannel, OutgoingChannel
from battleship.server.sessions import Listener, SessionRepository
from battleship.server.websocket import Client
from battleship.shared.events import EventMessage, ServerEvent
from battleship.shared.models import Action, Session


class GameHandler:
    def __init__(
        self,
        sessions: SessionRepository,
        in_channel: IncomingChannel,
        out_channel: OutgoingChannel,
    ):
        self._sessions = sessions
        self._in = in_channel
        self._out = out_channel
        self._games: dict[str, asyncio.Task[None]] = {}

    def start_new_game(self, host: Client, guest: Client, session: Session) -> None:
        game = Game(host, guest, session)
        task = asyncio.create_task(game.play())

        @logger.catch
        def cleanup(_: asyncio.Future[None]) -> None:
            self._games.pop(session.id, None)
            asyncio.create_task(self._sessions.delete(session.id))
            logger.trace("Game {session_id} is cleaned up.", session_id=session.id)

        task.add_done_callback(cleanup)
        self._games[session.id] = task

    def cancel_game(self, session_id: str) -> None:
        self._games[session_id].cancel()


class SessionSubscriptionHandler:
    def __init__(self, out_channel: OutgoingChannel, session_repository: SessionRepository):
        self._out = out_channel
        self._sessions = session_repository

    def make_session_observer(self, client_id: str) -> Listener:
        async def session_observer(session_id: str, action: Action) -> None:
            payload: dict[str, Any] = dict(action=action)

            if action == Action.ADD:
                payload["session"] = await self._sessions.get(session_id)

            if action in [Action.REMOVE, Action.START]:
                payload["session_id"] = session_id

            await self._out.publish(
                client_id,
                EventMessage(
                    kind=ServerEvent.SESSIONS_UPDATE,
                    payload=payload,
                ),
            )

        return session_observer

    def subscribe(self, client_id: str) -> None:
        self._sessions.subscribe(client_id, self.make_session_observer(client_id))

    def unsubscribe(self, client_id: str) -> None:
        self._sessions.unsubscribe(client_id)