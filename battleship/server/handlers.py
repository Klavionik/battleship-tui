import weakref
from typing import Any

from battleship.logger import server_logger as logger
from battleship.server.sessions import Sessions
from battleship.server.websocket import Client, EventHandler
from battleship.shared.events import ClientEvent, EventMessage, ServerEvent
from battleship.shared.models import Action


class GameHandler(EventHandler):
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

    async def handle(self, event: EventMessage) -> None:
        pass


class SessionSubscriptionHandler(EventHandler):
    def __init__(self, client: Client, session_repository: Sessions) -> None:
        self._client = weakref.ref(client)
        self._sessions = session_repository

    async def _session_observer(self, session_id: str, action: Action) -> None:
        logger.info(f"Session {session_id}, action {action.value}.")
        payload: dict[str, Any] = dict(action=action)

        if action == Action.ADD:
            payload["session"] = self._sessions.get(session_id)

        if action == Action.REMOVE:
            payload["session_id"] = session_id

        client = self._client()

        assert client, "Client should be garbage collected, but it is not"

        await client.send_event(
            EventMessage(
                kind=ServerEvent.SESSIONS_UPDATE,
                payload=payload,
            )
        )

    async def handle(self, event: EventMessage) -> None:
        match event:
            case EventMessage(kind=ClientEvent.SESSIONS_SUBSCRIBE):
                self._sessions.subscribe(self._session_observer)
            case EventMessage(kind=ClientEvent.SESSIONS_UNSUBSCRIBE):
                self._sessions.unsubscribe(self._session_observer)
