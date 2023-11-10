import asyncio

from blacksheep import FromJSON, Response, Router, WebSocket, created, ok
from blacksheep.server.authorization import allow_anonymous
from guardpost.authentication import Identity
from loguru import logger

from battleship.server.auth import AuthManager
from battleship.server.clients import ClientRepository
from battleship.server.handlers import GameHandler, SessionSubscriptionHandler
from battleship.server.pubsub import IncomingChannel, OutgoingChannel
from battleship.server.sessions import SessionRepository
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
    session_repository: SessionRepository,
    game_handler: GameHandler,
) -> None:
    nickname = identity.claims["nickname"]
    client = await client_repository.add(nickname)
    connection = Connection(client.id, websocket, in_channel, out_channel)

    await websocket.accept()
    logger.debug(f"{connection} accepted.")
    await connection.listen()
    logger.debug(f"{connection} disconnected.")
    subscription_handler.unsubscribe(client.id)

    current_session = await session_repository.get_for_client(client.id)

    if current_session:
        if current_session.started:
            game_handler.cancel_game(current_session.id)

        await session_repository.delete(current_session.id)

    await client_repository.delete(client.id)


@router.get("/sessions")
async def list_sessions(session_repository: SessionRepository) -> list[Session]:
    sessions = await session_repository.list()
    return [s for s in sessions if not s.started]


@router.post("/sessions")
async def create_session(
    identity: Identity,
    session: FromJSON[SessionCreate],
    session_repository: SessionRepository,
) -> Session:
    nickname = identity.claims["nickname"]
    return await session_repository.add(nickname, session.value)


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
    session_repository: SessionRepository,
) -> None:
    await session_repository.delete(session_id)


@router.post("/sessions/{session_id}/join")
async def join_session(
    identity: Identity,
    session_id: str,
    session_repository: SessionRepository,
    client_repository: ClientRepository,
    game_handler: GameHandler,
) -> None:
    guest_nickname = identity.claims["nickname"]
    session = await session_repository.get(session_id)
    players = await asyncio.gather(
        client_repository.get(session.host_id), client_repository.get(guest_nickname)
    )
    host, guest = players
    await session_repository.update(session.id, guest_id=guest.id, started=True)
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


@allow_anonymous()
@router.get("/healthz")
async def health() -> Response:
    return ok("OK")