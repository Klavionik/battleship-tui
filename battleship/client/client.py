import json
from asyncio import Task, create_task
from functools import cache
from typing import Any, Callable, Coroutine, Optional

from httpx import AsyncClient
from loguru import logger
from pyee.asyncio import AsyncIOEventEmitter

# noinspection PyProtectedMember
from websockets.client import WebSocketClientProtocol, connect

from battleship.client.auth import IDTokenAuth
from battleship.client.credentials import (
    Credentials,
    CredentialsProvider,
    FilesystemCredentialsProvider,
)
from battleship.shared.events import (
    ClientEvent,
    EventMessage,
    EventMessageData,
    ServerEvent,
)
from battleship.shared.models import (
    Action,
    IDToken,
    LoginData,
    Session,
    SessionID,
    User,
)


class SessionSubscription:
    def __init__(self) -> None:
        self._ee = AsyncIOEventEmitter()

    def on_add(self, callback: Callable[[Session], Coroutine[Any, Any, Any]]) -> None:
        self._ee.add_listener("add", callback)

    def on_remove(self, callback: Callable[[SessionID], Coroutine[Any, Any, Any]]) -> None:
        self._ee.add_listener("remove", callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._ee.emit(event, *args, **kwargs)


class Client:
    """
    Provides a convenient interface to the server API and realtime events.
    Handles the HTTP session, as well as the WebSocket connection. Publishes
    WebSocket messages as events via an async event emitter.
    """

    def __init__(self, host: str, port: int, credentials_provider: CredentialsProvider) -> None:
        self._host = host
        self._port = port
        self._ws: Optional[WebSocketClientProtocol] = None
        self._emitter = AsyncIOEventEmitter()
        self._publish_task: Task[None] | None = None
        self.user: User | None = None
        self.credentials: Credentials | None = None
        self.auth = IDTokenAuth()
        self._session = AsyncClient(base_url=self.base_url, auth=self.auth)
        self.credentials_provider = credentials_provider

        self.load_credentials()

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    @property
    def base_url_ws(self) -> str:
        return f"ws://{self._host}:{self._port}"

    async def connect(self) -> None:
        if self.credentials is None:
            raise RuntimeError("Must log in before trying to establish a WS connection.")

        self._ws = await connect(
            self.base_url_ws + "/ws",
            extra_headers={"Authorization": f"Bearer {self.credentials.id_token}"},
        )
        self._publish_task = create_task(self._publish_events())

    async def disconnect(self) -> None:
        if self._publish_task:
            self._publish_task.cancel()

        if self._ws:
            await self._ws.close()

    async def logout(self) -> None:
        self.user = None
        self.auth.clear_token()
        self.clear_credentials()

    async def login(self, nickname: str = "", password: str = "", *, guest: bool = False) -> str:
        if not guest and not (nickname and password):
            raise ValueError("Non-guest login must pass nickname and password.")

        if guest:
            endpoint = "/login/guest"
            payload = None
        else:
            endpoint = "/login"
            payload = dict(nickname=nickname, password=password)

        response = await self._session.post(endpoint, json=payload)
        data = response.json()
        login_data = LoginData(**data)
        credentials = Credentials.from_dict(
            dict(
                nickname=login_data.nickname,
                id_token=login_data.id_token,
                refresh_token=login_data.refresh_token,
                expires_at=login_data.expires_at,
            )
        )
        self.user = User(nickname=login_data.nickname)
        self.update_credentials(credentials)
        return self.user.nickname

    async def refresh_id_token(self, refresh_token: str) -> None:
        assert self.user

        payload = dict(refresh_token=refresh_token)
        response = await self._session.post("/refresh", json=payload)
        id_token = IDToken.from_dict(response.json())
        credentials = Credentials.from_dict(
            dict(
                nickname=self.user.nickname,
                id_token=id_token.id_token,
                refresh_token=refresh_token,
                expires_at=id_token.expires_at,
            )
        )
        self.update_credentials(credentials)

    def load_credentials(self) -> None:
        self.credentials = self.credentials_provider.load()

        if self.credentials:
            self.user = User(nickname=self.credentials.nickname)
            self.auth.set_token(self.credentials.id_token)

    def update_credentials(self, credentials: Credentials) -> None:
        self.credentials = credentials
        self.credentials_provider.save(credentials)
        self.auth.set_token(credentials.id_token)

    def clear_credentials(self) -> None:
        self.credentials = None
        self.credentials_provider.clear()

    async def create_session(
        self,
        name: str,
        roster: str,
        firing_order: str,
        salvo_mode: bool,
    ) -> Session:
        payload = dict(name=name, roster=roster, firing_order=firing_order, salvo_mode=salvo_mode)
        response = await self._session.post("/sessions", json=payload)
        return Session(**response.json())

    async def delete_session(self, session_id: SessionID) -> None:
        await self._session.delete(f"/sessions/{session_id}")

    async def fetch_sessions(self) -> list[Session]:
        response = await self._session.get("/sessions")
        return [Session(**data) for data in response.json()]

    async def sessions_subscribe(self) -> SessionSubscription:
        subscription = SessionSubscription()

        async def publish_update(payload: dict) -> None:  # type: ignore[type-arg]
            action = payload["action"].lower()
            kwargs: dict[str, str | Session] = {}

            if action == Action.ADD.lower():
                kwargs.update(session=Session(**payload["session"]))

            if action == Action.REMOVE.lower():
                kwargs.update(session_id=payload["session_id"])

            subscription.emit(action, **kwargs)

        self._emitter.add_listener(ServerEvent.SESSIONS_UPDATE, publish_update)
        await self._send(dict(kind=ClientEvent.SESSIONS_SUBSCRIBE))
        return subscription

    async def sessions_unsubscribe(self) -> None:
        await self._send(dict(kind=ClientEvent.SESSIONS_UNSUBSCRIBE))

    def add_listener(self, event: str, handler: Callable[..., Any]) -> None:
        self._emitter.add_listener(event, handler)

    async def _publish_events(self) -> None:
        if self._ws is None:
            raise RuntimeError("Cannot receive messages, no connection.")

        async for message in self._ws:
            event = EventMessage.from_raw(message)
            self._emitter.emit(event.kind, event.payload)

    async def _send(self, msg: EventMessageData) -> None:
        if self._ws is None:
            raise RuntimeError("Cannot send a message, no connection.")

        if self._ws.closed:
            logger.warning("Trying to send a message, but connection is closed.")
            return

        await self._ws.send(json.dumps(msg))


@cache
def get_client(host: str = "localhost", port: int = 8000) -> Client:
    return Client(host, port, FilesystemCredentialsProvider())
