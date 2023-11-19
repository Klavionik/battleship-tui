import asyncio
from typing import AsyncGenerator

from blacksheep import WebSocket, WebSocketDisconnectError
from loguru import logger

from battleship.server.pubsub import IncomingChannel, OutgoingChannel
from battleship.shared.events import EventMessage


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
        incoming_channel: IncomingChannel,
        outgoing_channel: OutgoingChannel,
    ):
        self.connection_id = connection_id
        self.nickname = nickname
        self.websocket = WebSocketWrapper(websocket)
        self._incoming = incoming_channel
        self._outgoing = outgoing_channel
        self._message_consumer = self._run_consumer()

    def __repr__(self) -> str:
        return f"<Connection {self.nickname} {self.websocket.client_ip}>"

    def __del__(self) -> None:
        logger.trace("{conn} was garbage collected.", conn=self)

    async def events(self) -> AsyncGenerator[EventMessage, None]:
        async for message in self.websocket:
            yield EventMessage.from_raw(message)

    async def listen(self) -> None:
        async for event in self.events():
            asyncio.create_task(self._incoming.publish(self.connection_id, event))

        self._message_consumer.cancel()
        del self._message_consumer

    async def send_event(self, event: EventMessage) -> None:
        await self.websocket.send_text(event.to_json())

    def _run_consumer(self) -> asyncio.Task[None]:
        @logger.catch
        async def consumer() -> None:
            try:
                async for _, event in self._outgoing.listen(self.connection_id):
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
        incoming_channel: IncomingChannel,
        outgoing_channel: OutgoingChannel,
    ) -> None:
        self.user_id = user_id
        self.nickname = nickname
        self.guest = guest
        self._incoming_channel = incoming_channel
        self._outgoing_channel = outgoing_channel

    def __repr__(self) -> str:
        return f"<Client: {self.nickname}>"

    def __del__(self) -> None:
        logger.trace("{client} was garbage collected.", client=self)

    @property
    def id(self) -> str:
        return self.user_id

    async def listen(self) -> AsyncGenerator[EventMessage, None]:
        async for _, event in self._incoming_channel.listen(self.id):
            yield event

    async def send_event(self, event: EventMessage) -> None:
        await self._outgoing_channel.publish(self.id, event)
