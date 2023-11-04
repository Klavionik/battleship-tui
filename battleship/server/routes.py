from blacksheep import FromJSON, Response, Router, WebSocket, created, no_content
from blacksheep.server.authorization import allow_anonymous
from guardpost.authentication import Identity

from battleship.logger import server_logger as logger
from battleship.server.auth import AuthManager
from battleship.server.clients import Clients
from battleship.server.handlers import GameHandler, SessionSubscriptionHandler
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
    client_repository: Clients,
    session_repository: Sessions,
) -> None:
    await websocket.accept()
    user = User(
        nickname=identity.claims["nickname"],
        guest=identity.has_claim_value("battleship/role", "guest"),
    )
    client = client_repository.add(websocket, user)
    handler = SessionSubscriptionHandler(client, session_repository)
    client.add_handler(handler)

    logger.debug(f"Handle client {client}.")
    await client.listen()
    logger.debug(f"Disconnect client {client}.")
    client_repository.remove(client.id)


@router.get("/sessions")
async def list_sessions(session_repository: Sessions) -> list[Session]:
    sessions = session_repository.list()
    return [s for s in sessions if not s.started]


@router.post("/sessions")
async def create_session(
    identity: Identity,
    session: FromJSON[SessionCreate],
    session_repository: Sessions,
) -> Session:
    nickname = identity.claims["nickname"]
    return session_repository.add(nickname, session.value)


@router.delete("/sessions/{session_id}")
async def remove_session(
    session_id: str,
    session_repository: Sessions,
) -> Response:
    session_repository.remove(session_id)
    return no_content()


@router.post("/sessions/{session_id}/join")
async def join_session(
    identity: Identity,
    session_id: str,
    session_repository: Sessions,
    client_repository: Clients,
) -> None:
    nickname = identity.claims["nickname"]
    session = session_repository.get(session_id)
    player, enemy = client_repository.get(session.host_id), client_repository.get(nickname)
    handler = GameHandler(player, enemy, session)
    player.add_handler(handler)
    enemy.add_handler(handler)
    session_repository.start(session.id, enemy.id)


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
