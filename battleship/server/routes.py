import asyncio

from blacksheep import (
    FromJSON,
    Response,
    Router,
    WebSocket,
    bad_request,
    created,
    forbidden,
    ok,
    unauthorized,
)
from blacksheep.server.authorization import allow_anonymous
from guardpost.authentication import Identity
from loguru import logger

from battleship.server.auth import AuthManager, InvalidSignup, WrongCredentials
from battleship.server.handlers import (
    GameHandler,
    PlayerSubscriptionHandler,
    SessionSubscriptionHandler,
)
from battleship.server.pubsub import IncomingChannel, OutgoingChannel
from battleship.server.repositories import (
    ClientRepository,
    SessionRepository,
    StatisticsRepository,
)
from battleship.server.repositories.statistics import StatisticsNotFound
from battleship.server.websocket import Connection
from battleship.shared.models import (
    IDToken,
    LoginCredentials,
    LoginData,
    PlayerCount,
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
    session_subscription_handler: SessionSubscriptionHandler,
    player_subscription_handler: PlayerSubscriptionHandler,
    session_repository: SessionRepository,
    game_handler: GameHandler,
) -> None:
    user_id = identity.claims["sub"]
    nickname = identity.claims["nickname"]
    guest = identity.has_claim_value("battleship/role", "guest")
    client = await client_repository.add(user_id, nickname, guest)
    connection = Connection(user_id, nickname, websocket, in_channel, out_channel)

    await websocket.accept()
    logger.debug(f"{connection} accepted.")
    await connection.listen()
    logger.debug(f"{connection} disconnected.")
    session_subscription_handler.unsubscribe(client.id)
    player_subscription_handler.unsubscribe(client.id)

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
    user_id = identity.claims["sub"]
    return await session_repository.add(user_id, session.value)


@router.post("/sessions/subscribe")
async def subscribe_to_session_updates(
    identity: Identity,
    client_repository: ClientRepository,
    subscription_handler: SessionSubscriptionHandler,
) -> None:
    client = await client_repository.get(identity.claims["sub"])
    subscription_handler.subscribe(client.id)


@router.post("/sessions/unsubscribe")
async def unsubscribe_from_session_updates(
    identity: Identity,
    client_repository: ClientRepository,
    subscription_handler: SessionSubscriptionHandler,
) -> None:
    client = await client_repository.get(identity.claims["sub"])
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
    guest_id = identity.claims["sub"]
    session = await session_repository.get(session_id)
    players = await asyncio.gather(
        client_repository.get(session.host_id), client_repository.get(guest_id)
    )
    host, guest = players
    await session_repository.update(session.id, guest_id=guest.id, started=True)
    game_handler.start_new_game(host, guest, session)


@router.get("/players/online")
async def get_players_online(
    client_repository: ClientRepository, session_repository: SessionRepository
) -> PlayerCount:
    players = await client_repository.count()
    sessions = await session_repository.list()
    started_sessions = [s for s in sessions if s.started]
    players_ingame = len(started_sessions) * 2
    return PlayerCount(total=players, ingame=players_ingame)


@router.post("/players/subscribe")
async def subscribe_to_player_count_updates(
    identity: Identity,
    client_repository: ClientRepository,
    player_subscription_handler: PlayerSubscriptionHandler,
) -> None:
    client = await client_repository.get(identity.claims["sub"])
    player_subscription_handler.subscribe(client.id)


@router.post("/players/unsubscribe")
async def unsubscribe_from_player_count_updates(
    identity: Identity,
    client_repository: ClientRepository,
    player_subscription_handler: PlayerSubscriptionHandler,
) -> None:
    client = await client_repository.get(identity.claims["sub"])
    player_subscription_handler.unsubscribe(client.id)


@allow_anonymous()
@router.post("/login/guest")
async def login_guest_user(auth_manager: AuthManager) -> LoginData:
    return await auth_manager.login_guest()


@allow_anonymous()
@router.post("/signup")
async def signup(credentials: SignupCredentials, auth_manager: AuthManager) -> Response:
    try:
        await auth_manager.signup(
            credentials.email,
            credentials.password,
            credentials.nickname,
        )
    except InvalidSignup:
        return bad_request()
    return created()


@allow_anonymous()
@router.post("/login")
async def login(credentials: LoginCredentials, auth_manager: AuthManager) -> LoginData | Response:
    try:
        return await auth_manager.login(credentials.nickname, credentials.password)
    except WrongCredentials:
        return unauthorized()


@allow_anonymous()
@router.post("/refresh")
async def refresh_id_token(refresh_token: RefreshToken, auth_manager: AuthManager) -> IDToken:
    return await auth_manager.refresh_id_token(refresh_token.refresh_token)


@allow_anonymous()
@router.get("/healthz")
async def health() -> Response:
    return ok("OK")


@router.get("/statistics/{player}")
async def get_player_statistics(
    identity: Identity, player: str, statistics_repository: StatisticsRepository
) -> Response:
    nickname = identity["nickname"]

    if nickname != player:
        return forbidden()

    user_id = identity["sub"]

    try:
        statistics = await statistics_repository.get(user_id)
    except StatisticsNotFound:
        statistics = await statistics_repository.create(user_id)

    return ok(statistics.to_dict())
