from blacksheep import Application, WebSocket

from battleship.server.connections import ConnectionManager
from battleship.server.players import Players
from battleship.server.sessions import Sessions

app = Application()

app.services.add_instance(ConnectionManager(Sessions(), Players()))


@app.router.ws("/ws")
async def ws(websocket: WebSocket, connection_handler: ConnectionManager) -> None:
    await websocket.accept()
    await connection_handler(websocket)
