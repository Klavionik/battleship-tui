import asyncio
import json as json_
from asyncio import Task
from typing import Any, AsyncIterator, Callable, Collection, Coroutine, Optional
from urllib.parse import urlparse

import httpx
import websockets
from httpx import AsyncClient, Request, Response
from loguru import logger
from pyee.asyncio import AsyncIOEventEmitter

# noinspection PyProtectedMember
from websockets.client import WebSocketClientProtocol, connect

from battleship.client.auth import IDTokenAuth
from battleship.client.credentials import Credentials, CredentialsProvider
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


class ClientError(Exception):
    pass


class WebSocketConnectionTimeout(ClientError):
    pass


class RequestFailed(ClientError):
    pass


class RefreshEvent:
    def __init__(self) -> None:
        self._event = asyncio.Event()

    async def wait(self) -> None:
        await self._event.wait()

    def refreshing(self) -> None:
        self._event.clear()

    def done(self) -> None:
        self._event.set()


class SessionSubscription:
    def __init__(self) -> None:
        self._ee = AsyncIOEventEmitter()

    def on_add(self, callback: Callable[[Session], Coroutine[Any, Any, Any]]) -> None:
        self._ee.add_listener(Action.ADD, callback)

    def on_remove(self, callback: Callable[[SessionID], Coroutine[Any, Any, Any]]) -> None:
        self._ee.add_listener(Action.REMOVE, callback)

    def on_start(self, callback: Callable[[SessionID], Coroutine[Any, Any, Any]]) -> None:
        self._ee.add_listener(Action.START, callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._ee.emit(event, *args, **kwargs)


class Client:
    """
    Provides a convenient interface to the server API and realtime events.
    Handles the HTTP session, as well as the WebSocket connection. Publishes
    WebSocket messages as events via an async event emitter.
    """

    def __init__(
        self,
        server_url: str,
        credentials_provider: CredentialsProvider,
        refresh_interval: int = 20,
        http_timeout: int = 20,
        ws_timeout: int = 30,
    ) -> None:
        parsed_url = urlparse(server_url)
        self._netloc = parsed_url.netloc
        self._scheme = parsed_url.scheme
        self._ws: Optional[WebSocketClientProtocol] = None
        self._ws_connected = asyncio.Event()
        self._ws_timeout = ws_timeout
        self._emitter = AsyncIOEventEmitter()
        self._events_worker_task: Task[None] | None = None
        self.user: User | None = None
        self.credentials: Credentials | None = None
        self.auth = IDTokenAuth()
        self._session = AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            timeout=http_timeout,
        )
        self._session.event_hooks = {"request": [log_request]}
        self.credentials_provider = credentials_provider

        self._refresh_interval = refresh_interval
        self._refresh_event = RefreshEvent()
        self._credentials_worker: Task[None] | None = None

    @property
    def base_url(self) -> str:
        return f"{self._scheme}://{self._netloc}"

    @property
    def base_url_ws(self) -> str:
        scheme = "wss" if self._scheme == "https" else "ws"
        return f"{scheme}://{self._netloc}"

    async def connect(self) -> None:
        if self.credentials is None:
            raise RuntimeError("Must log in before trying to establish a WS connection.")

        await self._refresh_event.wait()
        self._events_worker_task = self._run_events_worker()
        await self._ws_connected.wait()

    async def disconnect(self) -> None:
        if self._events_worker_task:
            logger.debug("Disconnect: cancel events worker.")
            self._events_worker_task.cancel()

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

        response = await self._request("POST", endpoint, json=payload)
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
        response = await self._request(
            "POST", "/refresh", json=payload, ensure_not_refreshing=False
        )
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
        logger.debug("Credentials loaded: {creds}.", creds=self.credentials)

        if self.credentials:
            self.user = User(nickname=self.credentials.nickname)
            self.auth.set_token(self.credentials.id_token)

        self._run_credentials_worker()

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
        payload = dict(
            name=name,
            roster=roster,
            firing_order=firing_order,
            salvo_mode=salvo_mode,
        )
        response = await self._request("POST", "/sessions", json=payload)
        return Session(**response.json())

    async def delete_session(self, session_id: SessionID) -> None:
        await self._request("DELETE", f"/sessions/{session_id}")

    async def fetch_sessions(self) -> list[Session]:
        response = await self._request("GET", "/sessions")
        return [Session(**data) for data in response.json()]

    async def sessions_subscribe(self) -> SessionSubscription:
        subscription = SessionSubscription()

        async def publish_update(payload: dict) -> None:  # type: ignore[type-arg]
            action = payload["action"]
            kwargs: dict[str, str | Session] = {}

            if action == Action.ADD:
                kwargs.update(session=Session(**payload["session"]))

            if action in [Action.REMOVE, Action.START]:
                kwargs.update(session_id=payload["session_id"])

            subscription.emit(action, **kwargs)

        self._emitter.add_listener(ServerEvent.SESSIONS_UPDATE, publish_update)
        await self._request("POST", url="/sessions/subscribe")
        return subscription

    async def sessions_unsubscribe(self) -> None:
        await self._request("POST", url="/sessions/unsubscribe")

    def add_listener(self, event: str, handler: Callable[..., Any]) -> None:
        self._emitter.add_listener(event, handler)

    def remove_listener(self, event: str, handler: Callable[..., Any]) -> None:
        self._emitter.remove_listener(event, handler)

    async def join_game(self, session_id: str) -> None:
        await self._request("POST", f"/sessions/{session_id}/join")

    async def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        payload = dict(ship_id=ship_id, position=position)
        await self._send(dict(kind=ClientEvent.SPAWN_SHIP, payload=payload))

    async def fire(self, position: Collection[str]) -> None:
        payload = dict(position=position)
        await self._send(dict(kind=ClientEvent.FIRE, payload=payload))

    async def cancel_game(self) -> None:
        await self._send(dict(kind=ClientEvent.CANCEL_GAME))

    async def _connect_with_retry(self) -> AsyncIterator[WebSocketClientProtocol]:
        assert self.credentials

        try:
            async with asyncio.timeout(self._ws_timeout) as timeout:
                async for connection in connect(
                    self.base_url_ws + "/ws",
                    extra_headers={"Authorization": f"Bearer {self.credentials.id_token}"},
                ):
                    timeout.reschedule(None)
                    yield connection
                    timeout.reschedule(asyncio.get_running_loop().time() + self._ws_timeout)
        except TimeoutError:
            logger.warning("Cannot establish WebSocket connection.")
            raise WebSocketConnectionTimeout("Cannot establish WebSocket connection.")

    async def _events_worker(self) -> None:
        logger.debug("Run events worker.")

        async for connection in self._connect_with_retry():
            logger.debug("Acquired new WebSocket connection.")
            self._ws = connection
            self._ws_connected.set()

            try:
                async for message in connection:
                    event = EventMessage.from_raw(message)
                    logger.debug("Received WebSocket event: {event}.", event=event)
                    self._emitter.emit(event.kind, event.payload)
            except websockets.ConnectionClosed:
                self._cleanup_ws()
                logger.warning("Server closed the WebSocket connection, acquire a new one.")
                continue

    def _cleanup_ws(self) -> None:
        logger.debug("WebSocket connection cleanup.")
        self._ws = None
        self._events_worker_task = None
        self._ws_connected.clear()

    def _run_events_worker(self) -> Task[None]:
        def cleanup(_: Task[None]) -> None:
            self._cleanup_ws()

        task = asyncio.create_task(self._events_worker())
        task.add_done_callback(cleanup)
        return task

    async def _send(self, msg: EventMessageData) -> None:
        if self._ws is None:
            raise RuntimeError("Cannot send a message, no connection.")

        if self._ws.closed:
            logger.warning("Trying to send a message, but connection is closed.")
            return

        await self._ws.send(json_.dumps(msg))

    async def _request(
        self,
        method: str,
        url: str,
        json: Any | None = None,
        ensure_not_refreshing: bool = True,
    ) -> Response:
        if ensure_not_refreshing:
            await self._refresh_event.wait()

        try:
            return await self._session.request(method, url, json=json)
        except httpx.TransportError as exc:
            logger.error("HTTP transport error occured: {exc}", exc=repr(exc))
            raise RequestFailed

    def _run_credentials_worker(self) -> None:
        async def credentials_worker() -> None:
            logger.debug("Start credentials worker.")

            try:
                while True:
                    if self.credentials and self.credentials.is_expired():
                        self._refresh_event.refreshing()
                        logger.debug("Credentials expired, refresh.")
                        await self.refresh_id_token(self.credentials.refresh_token)
                        self._refresh_event.done()
                    else:
                        # Refresh event is unset on client initialization to ensure
                        # we have a chance to refresh id token in case it expired
                        # before making any requests or trying to establish a WS connection.
                        self._refresh_event.done()

                    await asyncio.sleep(self._refresh_interval)
            except asyncio.CancelledError:
                logger.debug("Stop credentials worker.")
                raise

        self._credentials_worker = asyncio.create_task(credentials_worker())


async def log_request(request: Request) -> None:
    logger.debug(
        "Make {method} request to {path} with content {content}.",
        method=request.method,
        path=request.url.path,
        content=request.content.decode() if request.method in ["POST"] else None,
    )
