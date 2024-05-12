import asyncio
from time import time
from typing import Collection, Literal

from loguru import logger

from battleship.engine import create_game, domain
from battleship.engine.rosters import get_roster
from battleship.server import metrics
from battleship.server.bus import MessageBus
from battleship.server.repositories import (
    ClientRepository,
    SessionRepository,
    StatisticsRepository,
)
from battleship.shared.events import (
    ClientGameEvent,
    GameEvent,
    Message,
    ServerGameEvent,
)
from battleship.shared.models import (
    Client,
    GameSummary,
    Roster,
    Session,
    salvo_to_model,
)


class Game:
    def __init__(
        self, host: Client, guest: Client, session: Session, message_bus: MessageBus
    ) -> None:
        self.host = host
        self.guest = guest
        self.session_id = session.id
        self.roster = get_roster(session.roster)
        self.game = create_game(
            player_a=host.nickname,
            player_b=guest.nickname,
            roster=self.roster,
            firing_order=session.firing_order,
            salvo_mode=session.salvo_mode,
        )
        self.message_bus = message_bus
        self.summary = GameSummary()
        self.start: float = 0
        self.clients: dict[str, Client] = {host.nickname: host, guest.nickname: guest}
        self.players: dict[str, domain.Player] = {
            self.game.player_a.name: self.game.player_a,
            self.game.player_b.name: self.game.player_b,
        }

        self.game.on(domain.ShipSpawned, self.on_ship_spawned)
        self.game.on(domain.NextMove, self.on_next_move)
        self.game.on(domain.GameEnded, self.on_game_ended)

        self._event_queue: asyncio.Queue[Message[GameEvent]] = asyncio.Queue()
        self._background_tasks = [
            self._run_broadcaster(),
        ]
        self._stop_event = asyncio.Event()

    def __repr__(self) -> str:
        return f"<Game {self.session_id} | {self.host} vs {self.guest}>"

    def __del__(self) -> None:
        logger.trace("{game} was garbage collected.", game=self)

    def _run_broadcaster(self) -> asyncio.Task[None]:
        @logger.catch
        async def broadcaster() -> None:
            while True:
                event = await self._event_queue.get()

                for client in self.clients.values():
                    await self.message_bus.emit(f"clients.out.{client.id}", event)

                self._event_queue.task_done()

        return asyncio.create_task(broadcaster())

    def stop(self) -> None:
        self._stop_event.set()

    def broadcast(self, msg: Message[GameEvent]) -> None:
        self._event_queue.put_nowait(msg)

    def on_next_move(self, event: domain.NextMove) -> None:
        payload = dict(actor=event.actor.name, subject=event.subject.name)

        self.broadcast(
            Message(
                event=GameEvent(
                    type=ServerGameEvent.AWAITING_MOVE,
                    payload=payload,
                )
            )
        )

    def send_salvo(self, salvo: domain.Salvo) -> None:
        model = salvo_to_model(salvo)
        msg = Message[GameEvent](
            event=GameEvent(type=ServerGameEvent.SALVO, payload=dict(salvo=model.to_json()))
        )
        self.broadcast(msg)

    def on_game_ended(self, event: domain.GameEnded) -> None:
        self.summary.finalize(event.winner, start=self.start, end=time())

        msg = Message[GameEvent](
            event=GameEvent(
                type=ServerGameEvent.GAME_ENDED,
                payload=dict(winner=event.winner.name, summary=self.summary.to_json()),
            )
        )
        self.broadcast(msg)
        self.stop()

    def on_ship_spawned(
        self,
        event: domain.ShipSpawned,
    ) -> None:
        payload = dict(player=event.player.name, ship_id=event.ship_id, position=event.position)
        msg = Message[GameEvent](
            event=GameEvent(type=ServerGameEvent.SHIP_SPAWNED, payload=payload)
        )
        client = self.clients[event.player.name]
        asyncio.create_task(self.message_bus.emit(f"clients.out.{client.id}", msg))

        if event.fleet_ready:
            self.broadcast(
                Message(
                    event=GameEvent(
                        type=ServerGameEvent.FLEET_READY, payload=dict(player=event.player.name)
                    )
                )
            )

    def send_game_cancelled(
        self,
        reason: Literal["quit", "disconnect", "error"],
        by_player: str | None = None,
    ) -> None:
        metrics.games_cancelled_total.inc({"reason": reason})
        msg = Message[GameEvent](
            event=GameEvent(type=ServerGameEvent.GAME_CANCELLED, payload=dict(reason=reason))
        )

        if by_player is None:
            self.broadcast(msg)
        else:
            client = self.guest if self.host.nickname == by_player else self.host
            client = self.clients[client.nickname]
            asyncio.create_task(self.message_bus.emit(f"clients.out.{client.id}", msg))

    def announce_game_start(self) -> None:
        game_options = dict(
            roster=Roster.from_domain(self.roster).to_dict(),
            firing_order=self.game.firing_order,
            salvo_mode=self.game.salvo_mode,
        )

        asyncio.create_task(
            self.message_bus.emit(
                f"clients.out.{self.host.id}",
                Message(
                    event=GameEvent(
                        type=ServerGameEvent.START_GAME,
                        payload=dict(enemy=self.guest.nickname, **game_options),
                    )
                ),
            )
        )
        asyncio.create_task(
            self.message_bus.emit(
                f"clients.out.{self.guest.id}",
                Message(
                    event=GameEvent(
                        type=ServerGameEvent.START_GAME,
                        payload=dict(enemy=self.host.nickname, **game_options),
                    )
                ),
            )
        )

    async def play(self) -> GameSummary:
        metrics.games_started_total.inc({})
        self.connect_event_handlers()
        self.announce_game_start()
        self.start = time()

        try:
            await self._stop_event.wait()
            metrics.games_finished_total.inc({})
            return self.summary
        except asyncio.CancelledError:
            self.send_game_cancelled(reason="disconnect")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        await self._event_queue.join()

        while True:
            try:
                task = self._background_tasks.pop()
                task.cancel()
            except IndexError:
                break

        self.disconnect_event_handlers()

    def fire(self, position: Collection[str]) -> None:
        salvo = self.game.fire(position)
        self.summary.update_shots(salvo)
        self.send_salvo(salvo)
        self.game.turn(salvo)

    def add_ship(self, nickname: str, position: Collection[str], ship_id: str) -> None:
        player = self.players[nickname]
        self.game.add_ship(player, position, ship_id)

    def handle_client_event(self, client_nickname: str, message: Message[GameEvent]) -> None:
        logger.debug("Received message {message}", message=message)
        event = message.unwrap()

        try:
            match event:
                case GameEvent(type=ClientGameEvent.SPAWN_SHIP):
                    ship_id: str = event.payload["ship_id"]
                    position: Collection[str] = event.payload["position"]
                    self.add_ship(client_nickname, position, ship_id)
                case GameEvent(type=ClientGameEvent.FIRE):
                    position: Collection[str] = event.payload["position"]  # type: ignore[no-redef]
                    self.fire(position)
                case GameEvent(type=ClientGameEvent.CANCEL_GAME):
                    self.send_game_cancelled(reason="quit", by_player=client_nickname)
                    self.stop()
                case _:
                    logger.warning("Unknown event {event}", event=event)
        except Exception:  # noqa
            logger.exception(
                "An exception occured while handling a game event. Session ID {session_id}",
                session_id=self.session_id,
            )
            self.send_game_cancelled(reason="error")
            self.stop()

    async def handle_host_event(self, message: Message[GameEvent]) -> None:
        self.handle_client_event(self.host.nickname, message)

    async def handle_guest_event(self, message: Message[GameEvent]) -> None:
        self.handle_client_event(self.guest.nickname, message)

    def connect_event_handlers(self) -> None:
        self.message_bus.subscribe(f"clients.in.{self.host.id}", self.handle_host_event)
        self.message_bus.subscribe(f"clients.in.{self.guest.id}", self.handle_guest_event)

    def disconnect_event_handlers(self) -> None:
        self.message_bus.unsubscribe(f"clients.in.{self.host.id}", self.handle_host_event)
        self.message_bus.unsubscribe(f"clients.in.{self.guest.id}", self.handle_guest_event)


class GameManager:
    def __init__(
        self,
        sessions: SessionRepository,
        clients: ClientRepository,
        statistics: StatisticsRepository,
        message_bus: MessageBus,
    ):
        self._clients = clients
        self._sessions = sessions
        self._statistics = statistics
        self._message_bus = message_bus
        self._games: dict[str, tuple[Game, asyncio.Task[None]]] = {}

    def get_game(self, session_id: str) -> Game:
        game, _ = self._games[session_id]
        return game

    @logger.catch
    async def run_game(self, game: Game) -> None:
        try:
            metrics.games_now.inc({})
            summary = await game.play()
        finally:
            await self._sessions.delete(game.session_id)
            self._games.pop(game.session_id, None)
            logger.trace("Game {session_id} is cleaned up.", session_id=game.session_id)
            metrics.games_now.dec({})

        await self.save_game_summary(game, summary)

    async def save_game_summary(self, game: Game, summary: GameSummary) -> None:
        string_summary = summary.to_json()

        # Replace player nickname with their ID.
        string_summary = string_summary.replace(game.host.nickname, game.host.id).replace(
            game.guest.nickname, game.guest.id
        )

        summary = GameSummary.from_raw(string_summary)

        for client in (game.host, game.guest):
            if not client.guest:
                await self._statistics.save(client.id, summary)

    async def start_new_game(self, session_id: str) -> None:
        session = await self._sessions.get(session_id)
        players = await asyncio.gather(
            self._clients.get(session.host_id),
            self._clients.get(session.guest_id),
        )
        host, guest = players

        logger.debug(f"Start new game {host.nickname} vs. {guest.nickname}.")
        game = Game(host, guest, session, self._message_bus)
        await self._sessions.update(session.id, guest_id=guest.id, started=True)
        task = asyncio.create_task(self.run_game(game))
        self._games[session.id] = (game, task)

    def cancel_game(self, session_id: str) -> None:
        _, task = self._games[session_id]
        task.cancel()
