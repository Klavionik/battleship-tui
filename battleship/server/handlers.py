import asyncio
from typing import Any

from loguru import logger

from battleship.server.game import Game
from battleship.server.pubsub import IncomingChannel, OutgoingChannel
from battleship.server.sessions import Listener, SessionRepository
from battleship.server.statistics import StatisticsRepository
from battleship.server.websocket import Client
from battleship.shared.events import EventMessage, ServerEvent
from battleship.shared.models import Action, GameSummary, Session


class GameHandler:
    def __init__(
        self,
        sessions: SessionRepository,
        statistics: StatisticsRepository,
        in_channel: IncomingChannel,
        out_channel: OutgoingChannel,
    ):
        self._sessions = sessions
        self._statistics = statistics
        self._in = in_channel
        self._out = out_channel
        self._games: dict[str, asyncio.Task[None]] = {}

    @logger.catch
    async def run_game(self, game: Game) -> None:
        summary = await game.play()
        string_summary = summary.to_json()

        # Replace player nickname with their ID.
        string_summary = string_summary.replace(game.host.nickname, game.host.user_id).replace(
            game.guest.nickname, game.guest.user_id
        )

        summary = GameSummary.from_raw(string_summary)

        for _, player in game.clients.items():
            if not player.guest:
                await self._statistics.save(player.user_id, summary)

    def start_new_game(self, host: Client, guest: Client, session: Session) -> None:
        logger.debug(f"Start new game {host.nickname} vs. {guest.nickname}.")
        game = Game(host, guest, session)
        task = asyncio.create_task(self.run_game(game))

        def cleanup(_: asyncio.Task[None]) -> None:
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
