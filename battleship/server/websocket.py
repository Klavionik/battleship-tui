import asyncio
from typing import AsyncGenerator, AsyncIterator

from blacksheep import WebSocket, WebSocketDisconnectError
from loguru import logger

from battleship.server.pubsub import Broker, Channel
from battleship.shared.events import GameEvent, Message, NotificationEvent

ClientMessage = Message[GameEvent] | Message[NotificationEvent]


class ClientInChannel(Channel[ClientMessage]):
    def __init__(self, broker: Broker):
        super().__init__("clients.in", broker)


class ClientOutChannel(Channel[ClientMessage]):
    def __init__(self, broker: Broker):
        super().__init__("clients.out", broker)


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
        connection_id: str,
        nickname: str,
        websocket: WebSocket,
        incoming_channel: ClientInChannel,
        outgoing_channel: ClientOutChannel,
    ):
        self.connection_id = connection_id
        self.nickname = nickname
        self.websocket = WebSocketWrapper(websocket)
        self._incoming = incoming_channel.topic(self.connection_id)
        self._outgoing = outgoing_channel.topic(self.connection_id)
        self._message_consumer = self._run_consumer()

    def __repr__(self) -> str:
        return f"<Connection {self.nickname} {self.websocket.client_ip}>"

    def __del__(self) -> None:
        logger.trace("{conn} was garbage collected.", conn=self)

    async def messages(self) -> AsyncIterator[str]:
        async for message in self.websocket:
            yield message

    async def listen(self) -> None:
        async for ws_message in self.messages():
            message: ClientMessage = Message.from_raw(ws_message)
            asyncio.create_task(self._incoming.publish(message))

        self._message_consumer.cancel()
        del self._message_consumer

    async def send_event(self, event: ClientMessage) -> None:
        await self.websocket.send_text(event.to_json())

    def _run_consumer(self) -> asyncio.Task[None]:
        @logger.catch
        async def consumer() -> None:
            try:
                async for event in self._outgoing.listen():
                    await self.send_event(event)
            except asyncio.CancelledError:
                logger.debug("{conn} Stop message consumer.", conn=self)
                raise

        return asyncio.create_task(consumer())


class Client:
    def __init__(
        self,
        user_id: str,
        nickname: str,
        guest: bool,
        version: str,
        incoming_channel: ClientInChannel,
        outgoing_channel: ClientOutChannel,
    ) -> None:
        self.user_id = user_id
        self.nickname = nickname
        self.guest = guest
        self.version = version
        self._incoming_channel = incoming_channel.topic(self.id)
        self._outgoing_channel = outgoing_channel.topic(self.id)

    def __repr__(self) -> str:
        return f"<Client: {self.nickname}>"

    def __del__(self) -> None:
        logger.trace("{client} was garbage collected.", client=self)

    @property
    def id(self) -> str:
        return self.user_id

    async def listen(self) -> AsyncIterator[ClientMessage]:
        async for event in self._incoming_channel.listen():
            yield event

    async def send_event(self, event: ClientMessage) -> None:
        await self._outgoing_channel.publish(event)
