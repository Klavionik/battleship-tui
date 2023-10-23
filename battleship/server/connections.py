from typing import Any, AsyncGenerator

from blacksheep import WebSocket, WebSocketDisconnectError
from loguru import logger

from battleship.server.sessions import Sessions
from battleship.shared.events import ClientEvent, EventMessage, ServerEvent
from battleship.shared.models import Action


class WebSocketWrapper:
    def __init__(self, socket: WebSocket):
        self.socket = socket

    async def __aiter__(self) -> AsyncGenerator[str, None]:
        while True:
            try:
                yield await self.socket.receive_text()
            except WebSocketDisconnectError:
                break


class Client:
    def __init__(
        self,
        connection: WebSocket,
        sessions_repository: Sessions,
    ) -> None:
        self._connection = WebSocketWrapper(connection)
        self._sessions = sessions_repository

    @property
    def local_address(self) -> str:
        return self._connection.socket.client_ip

    async def close(self) -> None:
        await self._connection.socket.close()

    async def send_event(self, event: EventMessage) -> None:
        await self._connection.socket.send_text(event.to_json())

    async def _session_observer(self, session_id: str, action: Action) -> None:
        logger.info(f"Send session update for {session_id=}, {action=}.")
        payload: dict[str, Any] = dict(action=action)

        if action == Action.ADD:
            payload["session"] = self._sessions.get(session_id)

        if action == Action.REMOVE:
            payload["session_id"] = session_id

        await self.send_event(
            EventMessage(
                kind=ServerEvent.SESSIONS_UPDATE,
                payload=payload,
            )
        )

    async def __aiter__(self) -> AsyncGenerator[EventMessage, None]:
        async for message in self._connection:
            yield EventMessage.from_raw(message)

    async def __call__(self) -> None:
        async for event in self:
            logger.info(event)
            match event:
                case EventMessage(kind=ClientEvent.SESSIONS_SUBSCRIBE):
                    self._sessions.subscribe(self._session_observer)
                case EventMessage(kind=ClientEvent.SESSIONS_UNSUBSCRIBE):
                    self._sessions.unsubscribe(self._session_observer)


class ConnectionManager:
    def __init__(self, sessions_repository: Sessions) -> None:
        self.clients: set[Client] = set()
        self._sessions = sessions_repository

    async def __call__(self, socket: WebSocket) -> None:
        client = Client(socket, self._sessions)
        self.clients.add(client)

        await client()

        self.clients.remove(client)
