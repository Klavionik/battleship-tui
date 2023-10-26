from blacksheep import FromJSON, Response, Router, WebSocket, created, no_content
from blacksheep.server.authorization import allow_anonymous
from guardpost.authentication import Identity

from battleship.server.auth import AuthManager
from battleship.server.connections import ConnectionManager
from battleship.server.sessions import Sessions
from battleship.shared.models import (
    IDToken,
    LoginCredentials,
    LoginData,
    RefreshToken,
    Session,
    SessionCreate,
    SignupCredentials,
    User,
)

router = Router()  # type: ignore[no-untyped-call]


@router.ws("/ws")
async def ws(
    websocket: WebSocket,
    identity: Identity,
    connection_handler: ConnectionManager,
) -> None:
    await websocket.accept()
    user = User(
        nickname=identity.claims["nickname"],
        guest=identity.has_claim_value("battleship/role", "guest"),
    )
    await connection_handler(websocket, user)


@router.get("/sessions")
async def list_sessions(session_repository: Sessions) -> list[Session]:
    return session_repository.list()


@router.post("/sessions")
async def create_session(
    session: FromJSON[SessionCreate],
    session_repository: Sessions,
) -> Session:
    return session_repository.add(session.value)


@router.delete("/sessions/{session_id}")
async def remove_session(
    session_id: str,
    session_repository: Sessions,
) -> Response:
    session_repository.remove(session_id)
    return no_content()


@allow_anonymous()
@router.post("/login/guest")
async def login_guest_user(auth_manager: AuthManager) -> LoginData:
    return await auth_manager.login_guest()


@allow_anonymous()
@router.post("/signup")
async def signup(credentials: SignupCredentials, auth_manager: AuthManager) -> Response:
    await auth_manager.signup(
        credentials.email,
        credentials.password,
        credentials.nickname,
    )
    return created()


@allow_anonymous()
@router.post("/login")
async def login(credentials: LoginCredentials, auth_manager: AuthManager) -> LoginData:
    return await auth_manager.login(credentials.nickname, credentials.password)


@allow_anonymous()
@router.post("/refresh")
async def refresh_id_token(refresh_token: RefreshToken, auth_manager: AuthManager) -> IDToken:
    return await auth_manager.refresh_id_token(refresh_token.refresh_token)
