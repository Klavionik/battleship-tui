from typing import Any, AsyncGenerator, AsyncIterator

from blacksheep import WebSocket, WebSocketDisconnectError
from loguru import logger

from battleship.server import metrics
from battleship.server.bus import MessageBus
from battleship.server.repositories import SubscriptionRepository
from battleship.shared.events import GameEvent, Message, NotificationEvent

ClientMessage = Message[GameEvent] | Message[NotificationEvent]


class WebSocketWrapper:
    def __init__(self, socket: WebSocket):
        self._socket = socket

    def __repr__(self) -> str:
        return f"<WebSocket {self.client_ip}>"

    @property
    def client_ip(self) -> str:
        return self._socket.client_ip

    async def send_text(self, text: str) -> None:
        await self._socket.send_text(text)

    async def __aiter__(self) -> AsyncGenerator[str, None]:
        while True:
            try:
                text = await self._socket.receive_text()
                logger.trace(
                    "{ws} Message received {message}",
                    ws=self,
                    message=text,
                )
                yield text
            except WebSocketDisconnectError:
                break


class Connection:
    def __init__(
        self,
        user_id: str,
        nickname: str,
        websocket: WebSocket,
        message_bus: MessageBus,
        subscription_repository: SubscriptionRepository,
    ):
        self.connection_id = user_id
        self.nickname = nickname
        self._websocket = WebSocketWrapper(websocket)
        self._message_bus = message_bus
        self._subscription_repository = subscription_repository

    def __repr__(self) -> str:
        return f"<Connection {self.nickname} {self._websocket.client_ip}>"

    def __enter__(self) -> None:
        self._message_bus.subscribe("notifications", self._handle_notification_event)
        self._message_bus.subscribe(f"clients.out.{self.connection_id}", self.send_event)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._message_bus.unsubscribe("notifications", self._handle_notification_event)
        self._message_bus.unsubscribe(f"clients.out.{self.connection_id}", self.send_event)

    def __del__(self) -> None:
        logger.trace("{conn} was garbage collected.", conn=self)

    async def messages(self) -> AsyncIterator[str]:
        async for message in self._websocket:
            yield message

    async def listen(self) -> None:
        async for ws_message in self.messages():
            message: ClientMessage = Message.from_raw(ws_message)
            await self._message_bus.emit(f"clients.in.{self.connection_id}", message)
            metrics.websocket_messages_in.inc(
                {"client": self.nickname, "connection_id": self.connection_id}
            )

    async def send_event(self, event: ClientMessage) -> None:
        await self._websocket.send_text(event.to_json())
        metrics.websocket_messages_out.inc(
            {"client": self.nickname, "connection_id": self.connection_id}
        )

    async def _handle_notification_event(self, message: Message[NotificationEvent]) -> None:
        event = message.unwrap()
        subscribers = await self._subscription_repository.get_subscribers(event.subscription)

        if self.connection_id in subscribers:
            await self.send_event(message)
