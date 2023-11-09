import asyncio

from blacksheep import FromJSON, Response, Router, WebSocket, created
from blacksheep.server.authorization import allow_anonymous
from guardpost.authentication import Identity
from loguru import logger

from battleship.server.auth import AuthManager
from battleship.server.clients import ClientRepository
from battleship.server.handlers import GameHandler, SessionSubscriptionHandler
from battleship.server.pubsub import IncomingChannel, OutgoingChannel
from battleship.server.sessions import Sessions
from battleship.server.websocket import Connection
from battleship.shared.models import (
    IDToken,
    LoginCredentials,
    LoginData,
    RefreshToken,
    Session,
    SessionCreate,
    SignupCredentials,
)

router = Router()  # type: ignore[no-untyped-call]


@router.ws("/ws")
async def ws(
    websocket: WebSocket,
    identity: Identity,
    client_repository: ClientRepository,
    in_channel: IncomingChannel,
    out_channel: OutgoingChannel,
    subscription_handler: SessionSubscriptionHandler,
) -> None:
    nickname = identity.claims["nickname"]
    client = await client_repository.add(nickname)
    connection = Connection(client.id, websocket, in_channel, out_channel)

    await websocket.accept()
    logger.debug(f"{connection} accepted.")
    await connection.listen()
    logger.debug(f"{connection} disconnected.")
    subscription_handler.unsubscribe(client.id)
    await client_repository.delete(client.id)


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


@router.post("/sessions/subscribe")
async def subscribe_to_session_updates(
    identity: Identity,
    client_repository: ClientRepository,
    subscription_handler: SessionSubscriptionHandler,
) -> None:
    client = await client_repository.get(identity.claims["nickname"])
    subscription_handler.subscribe(client.id)


@router.post("/sessions/unsubscribe")
async def unsubscribe_from_session_updates(
    identity: Identity,
    client_repository: ClientRepository,
    subscription_handler: SessionSubscriptionHandler,
) -> None:
    client = await client_repository.get(identity.claims["nickname"])
    subscription_handler.unsubscribe(client.id)


@router.delete("/sessions/{session_id}")
async def remove_session(
    session_id: str,
    session_repository: Sessions,
) -> None:
    session_repository.remove(session_id)


@router.post("/sessions/{session_id}/join")
async def join_session(
    identity: Identity,
    session_id: str,
    session_repository: Sessions,
    client_repository: ClientRepository,
    game_handler: GameHandler,
) -> None:
    guest_nickname = identity.claims["nickname"]
    session = session_repository.get(session_id)
    players = await asyncio.gather(
        client_repository.get(session.host_id), client_repository.get(guest_nickname)
    )
    host, guest = players
    session_repository.start(session.id, guest.id)
    game_handler.start_new_game(host, guest, session)


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
