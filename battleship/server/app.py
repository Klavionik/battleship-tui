from blacksheep import Application, WebSocket

from battleship.server.connections import ConnectionManager
from battleship.server.players import Players
from battleship.server.sessions import Sessions
from battleship.shared.sessions import Session

app = Application()

app.services.add_singleton(Sessions)
app.services.add_singleton(Players)
app.services.add_singleton(ConnectionManager)


@app.router.ws("/ws")
async def ws(websocket: WebSocket, connection_handler: ConnectionManager) -> None:
    await websocket.accept()
    await connection_handler(websocket)


@app.router.get("/sessions")
async def list_sessions(session_repository: Sessions) -> list[Session]:
    return session_repository.list()
