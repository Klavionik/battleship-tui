import asyncio
from dataclasses import asdict
from time import time
from typing import Collection, Literal

from loguru import logger

from battleship.engine import create_game, domain
from battleship.engine.roster import get_roster
from battleship.server.websocket import Client
from battleship.shared.events import ClientEvent, EventMessage, ServerEvent
from battleship.shared.models import GameSummary, Session, salvo_to_model


class Game:
    def __init__(
        self,
        host: Client,
        guest: Client,
        session: Session,
    ) -> None:
        self.session_id = session.id
        self.host = host
        self.guest = guest
        self.roster = get_roster(session.roster)
        self.game = create_game(
            player_a=host.nickname,
            player_b=guest.nickname,
            roster=self.roster,
            firing_order=session.firing_order,
            salvo_mode=session.salvo_mode,
        )
        self.summary = GameSummary()
        self.started: float | None = None
        self.clients: dict[str, Client] = {host.nickname: host, guest.nickname: guest}
        self.players: dict[str, domain.Player] = {
            self.game.player_a.name: self.game.player_a,
            self.game.player_b.name: self.game.player_b,
        }

        self.game.register_hook(domain.Hook.SHIP_ADDED, self.send_ship_spawned)
        self.game.register_hook(domain.Hook.FLEET_READY, self.send_fleet_ready)
        self.game.register_hook(domain.Hook.NEXT_MOVE, self.send_awaiting_move)
        self.game.register_hook(domain.Hook.GAME_ENDED, self.send_winner)

        self._event_queue: asyncio.Queue[EventMessage] = asyncio.Queue()
        self._consumers = [self._run_consumer(self.host), self._run_consumer(self.guest)]
        self._broadcaster = self._run_broadcaster()
        self._stop_event = asyncio.Event()

    def __repr__(self) -> str:
        return f"<Game {self.session_id} | {self.host.nickname} vs {self.guest.nickname}>"

    def __del__(self) -> None:
        logger.trace("{game} was garbage collected.", game=self)

    def _run_broadcaster(self) -> asyncio.Task[None]:
        @logger.catch
        async def broadcaster() -> None:
            while True:
                event = await self._event_queue.get()

                for client in self.clients.values():
                    await client.send_event(event)

                self._event_queue.task_done()

        return asyncio.create_task(broadcaster())

    def _run_consumer(self, client: Client) -> asyncio.Task[None]:
        @logger.catch
        async def consumer() -> None:
            async for event in client.listen():
                self.handle(client.nickname, event)

        return asyncio.create_task(consumer())

    def stop(self) -> None:
        self._stop_event.set()

    def broadcast(self, event: EventMessage) -> None:
        self._event_queue.put_nowait(event)

    def send_awaiting_move(self, game: domain.Game) -> None:
        payload = dict(actor=game.current_player.name, subject=game.player_under_attack.name)

        self.broadcast(
            EventMessage(
                kind=ServerEvent.AWAITING_MOVE,
                payload=payload,
            )
        )

    def send_fleet_ready(self, player: domain.Player) -> None:
        self.broadcast(EventMessage(kind=ServerEvent.FLEET_READY, payload=dict(player=player.name)))

    def send_salvo(self, salvo: domain.Salvo) -> None:
        model = salvo_to_model(salvo)
        event = EventMessage(kind=ServerEvent.SALVO, payload=dict(salvo=model.to_json()))
        self.broadcast(event)
        self.update_summary_shots(salvo)

    def send_winner(self, game: domain.Game) -> None:
        assert game.winner
        self.finalize_summary(game)
        event = EventMessage(
            kind=ServerEvent.GAME_ENDED,
            payload=dict(winner=game.winner.name, summary=self.summary.to_json()),
        )
        self.broadcast(event)
        self.stop()

    def send_ship_spawned(
        self,
        player: domain.Player,
        ship_id: str,
        position: Collection[str],
    ) -> None:
        payload = dict(player=player.name, ship_id=ship_id, position=position)
        event = EventMessage(kind=ServerEvent.SHIP_SPAWNED, payload=payload)
        asyncio.create_task(self.clients[player.name].send_event(event))

    def send_game_cancelled(
        self,
        reason: Literal["quit", "disconnect"],
        by_player: str | None = None,
    ) -> None:
        event = EventMessage(kind=ServerEvent.GAME_CANCELLED, payload=dict(reason=reason))

        if by_player is None:
            self.broadcast(event)
        else:
            client = self.guest if self.host.nickname == by_player else self.host
            asyncio.create_task(client.send_event(event))

    def announce_game_start(self) -> None:
        asyncio.create_task(
            self.host.send_event(
                EventMessage(
                    kind=ServerEvent.START_GAME,
                    payload=dict(enemy=self.guest.nickname, roster=asdict(self.roster)),
                )
            )
        )
        asyncio.create_task(
            self.guest.send_event(
                EventMessage(
                    kind=ServerEvent.START_GAME,
                    payload=dict(enemy=self.host.nickname, roster=asdict(self.roster)),
                )
            )
        )

    async def play(self) -> None:
        self.announce_game_start()
        self.started = time()

        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            self.send_game_cancelled(reason="disconnect")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        while True:
            try:
                consumer = self._consumers.pop()
                consumer.cancel()
            except IndexError:
                break

        await self._event_queue.join()
        self._broadcaster.cancel()
        del self._broadcaster
        self.game.clear_hooks()

    def update_summary_shots(self, salvo: domain.Salvo) -> None:
        client = self.clients[salvo.actor.name]

        for _ in salvo:
            self.summary.add_shot(client.user_id)

    def finalize_summary(self, game: domain.Game) -> None:
        winner = game.winner

        assert winner
        assert self.started

        self.summary.winner = self.clients[winner.name].user_id
        self.summary.duration = int(time() - self.started)
        self.summary.ships_left = winner.ships_alive

        for ship in winner.ships:
            self.summary.hp_left += ship.hp

    @logger.catch
    def handle(self, client_nickname: str, event: EventMessage) -> None:
        match event:
            case EventMessage(kind=ClientEvent.SPAWN_SHIP):
                ship_id: str = event.payload["ship_id"]
                position: Collection[str] = event.payload["position"]
                player = self.players[client_nickname]
                self.game.add_ship(player, position, ship_id)
            case EventMessage(kind=ClientEvent.FIRE):
                position = event.payload["position"]
                salvo = self.game.fire(position)
                self.send_salvo(salvo)
                self.game.turn(salvo)
            case EventMessage(kind=ClientEvent.CANCEL_GAME):
                self.send_game_cancelled(reason="quit", by_player=client_nickname)
                self.stop()
