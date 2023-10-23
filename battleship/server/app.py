from blacksheep import (
    Application,
    FromJSON,
    Response,
    WebSocket,
    no_content,
    unauthorized,
)

from battleship.server.auth import (
    AuthManager,
    FirebaseAuthManager,
    TokenHeader,
    UserVerificationFailed,
)
from battleship.server.config import Config, get_config
from battleship.server.connections import ConnectionManager
from battleship.server.sessions import Sessions
from battleship.shared.models import Session, SessionCreate, User

app = Application()

app.services.add_singleton_by_factory(get_config, Config)
app.services.add_singleton(AuthManager, FirebaseAuthManager)
app.services.add_singleton(Sessions)
app.services.add_singleton(ConnectionManager)


@app.router.ws("/ws")
async def ws(
    websocket: WebSocket,
    id_token: TokenHeader,
    connection_handler: ConnectionManager,
    auth_manager: AuthManager,
) -> Response | None:
    try:
        user = await auth_manager.verify_user(id_token.value)
    except UserVerificationFailed:
        return unauthorized()

    await websocket.accept()
    await connection_handler(websocket, user)


@app.router.get("/sessions")
async def list_sessions(session_repository: Sessions) -> list[Session]:
    return session_repository.list()


@app.router.post("/sessions")
async def create_session(
    session: FromJSON[SessionCreate],
    session_repository: Sessions,
) -> Session:
    return session_repository.add(session.value)


@app.router.delete("/sessions/{session_id}")
async def remove_session(
    session_id: str,
    session_repository: Sessions,
) -> Response:
    session_repository.remove(session_id)
    return no_content()


@app.router.post("/login/guest")
async def login_guest_user(auth_manager: AuthManager) -> User:
    return await auth_manager.login_guest()
