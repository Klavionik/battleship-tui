from blacksheep import WebSocket

from battleship.server.websocket import Client
from battleship.shared.models import User


class Clients:
    def __init__(self) -> None:
        self._clients: dict[str, Client] = {}

    def add(self, client_id: str, socket: WebSocket, user: User) -> Client:
        client = Client(client_id, socket, user)
        self._clients[client_id] = client
        return client

    def get(self, client_id: str) -> Client:
        return self._clients[client_id]

    def list(self) -> list[Client]:
        return list(self._clients.values())

    def remove(self, client_id: str) -> None:
        self._clients.pop(client_id, None)
