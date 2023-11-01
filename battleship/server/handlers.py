from typing import Any

from battleship.logger import server_logger as logger
from battleship.server.clients import Clients
from battleship.server.sessions import Sessions
from battleship.server.websocket import Client
from battleship.shared.events import ClientEvent, EventMessage, ServerEvent
from battleship.shared.models import Action


class SessionHandler:
    def __init__(self, client_a: Client, client_b: Client) -> None:
        self.client_a = client_a
        self.client_b = client_b
        self.clients = (client_a, client_b)

    async def __call__(self) -> None:
        await self.client_a.send_event(
            EventMessage(
                kind=ServerEvent.START_GAME, payload=dict(enemy=self.client_b.user.nickname)
            )
        )
        await self.client_b.send_event(
            EventMessage(
                kind=ServerEvent.START_GAME, payload=dict(enemy=self.client_a.user.nickname)
            )
        )


class ConnectionHandler:
    def __init__(
        self, client: Client, session_repository: Sessions, client_repository: Clients
    ) -> None:
        self._client = client
        self._sessions = session_repository
        self._clients = client_repository

    async def _session_observer(self, session_id: str, action: Action) -> None:
        logger.info(f"Session {session_id}, action {action.value}.")
        payload: dict[str, Any] = dict(action=action)

        if action == Action.ADD:
            payload["session"] = self._sessions.get(session_id)

        if action == Action.REMOVE:
            payload["session_id"] = session_id

        await self._client.send_event(
            EventMessage(
                kind=ServerEvent.SESSIONS_UPDATE,
                payload=payload,
            )
        )

    async def __call__(self) -> None:
        async for event in self._client:
            logger.info(event)
            match event:
                case EventMessage(kind=ClientEvent.SESSIONS_SUBSCRIBE):
                    self._sessions.subscribe(self._session_observer)
                case EventMessage(kind=ClientEvent.SESSIONS_UNSUBSCRIBE):
                    self._sessions.unsubscribe(self._session_observer)
