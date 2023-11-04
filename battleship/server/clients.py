from blacksheep import WebSocket

from battleship.server.websocket import Client
from battleship.shared.models import User


class Clients:
    def __init__(self) -> None:
        self._clients: dict[str, Client] = {}

    def add(self, socket: WebSocket, user: User) -> Client:
        client = Client(socket, user)
        self._clients[client.id] = client
        return client

    def get(self, nickname: str) -> Client:
        return self._clients[nickname]

    def list(self) -> list[Client]:
        return list(self._clients.values())

    def remove(self, nickname: str) -> None:
        self._clients.pop(nickname, None)
