import asyncio
import weakref
from dataclasses import asdict
from typing import Any, Collection

from battleship.engine import create_game, domain
from battleship.engine.roster import get_roster
from battleship.logger import server_logger as logger
from battleship.server.sessions import Sessions
from battleship.server.websocket import Client, EventHandler
from battleship.shared.events import ClientEvent, EventMessage, ServerEvent
from battleship.shared.models import Action, Session, salvo_to_model


class GameHandler(EventHandler):
    def __init__(self, client_a: Client, client_b: Client, session: Session) -> None:
        self.client_a = client_a
        self.client_b = client_b
        self.clients = {client_a.id: client_a, client_b.id: client_b}
        self.roster = get_roster(session.roster)
        self.game = create_game(
            player_a=client_a.user.nickname,
            player_b=client_b.user.nickname,
            roster=self.roster,
            firing_order=session.firing_order,
            salvo_mode=session.salvo_mode,
        )
        self.players = {client_a.id: self.game.player_a, client_b.id: self.game.player_b}

        self.game.register_hook(domain.Hook.SHIP_ADDED, self.send_ship_spawned)
        self.game.register_hook(domain.Hook.FLEET_READY, self.send_fleet_ready)
        self.game.register_hook(domain.Hook.NEXT_MOVE, self.send_awaiting_move)
        self.game.register_hook(domain.Hook.GAME_ENDED, self.send_winner)

        self.announce_game_start()

    def broadcast(self, event: EventMessage) -> None:
        for client in self.clients.values():
            asyncio.create_task(client.send_event(event))

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

    def send_winner(self, game: domain.Game) -> None:
        assert game.winner
        event = EventMessage(kind=ServerEvent.GAME_ENDED, payload=dict(winner=game.winner.name))
        self.broadcast(event)

    def send_ship_spawned(
        self,
        player: domain.Player,
        ship_id: str,
        position: Collection[str],
    ) -> None:
        client_id = next(
            client_id for client_id, player_ in self.players.items() if player_ is player
        )
        payload = dict(player=player.name, ship_id=ship_id, position=position)
        event = EventMessage(kind=ServerEvent.SHIP_SPAWNED, payload=payload)
        asyncio.create_task(self.clients[client_id].send_event(event))

    def announce_game_start(self) -> None:
        asyncio.create_task(
            self.client_a.send_event(
                EventMessage(
                    kind=ServerEvent.START_GAME,
                    payload=dict(enemy=self.client_b.user.nickname, roster=asdict(self.roster)),
                )
            )
        )
        asyncio.create_task(
            self.client_b.send_event(
                EventMessage(
                    kind=ServerEvent.START_GAME,
                    payload=dict(enemy=self.client_a.user.nickname, roster=asdict(self.roster)),
                )
            )
        )

    async def handle(self, client: Client, event: EventMessage) -> None:
        match event:
            case EventMessage(kind=ClientEvent.SPAWN_SHIP):
                ship_id: str = event.payload["ship_id"]
                position: Collection[str] = event.payload["position"]
                player = self.players[client.id]
                self.game.add_ship(player, position, ship_id)
            case EventMessage(kind=ClientEvent.FIRE):
                position = event.payload["position"]
                salvo = self.game.fire(position)
                self.send_salvo(salvo)
                self.game.turn(salvo)


class SessionSubscriptionHandler(EventHandler):
    def __init__(self, client: Client, session_repository: Sessions) -> None:
        self._client = weakref.ref(client)
        self._sessions = session_repository

    async def _session_observer(self, session_id: str, action: Action) -> None:
        logger.info(f"Session {session_id}, action {action.value}.")
        payload: dict[str, Any] = dict(action=action)

        if action == Action.ADD:
            payload["session"] = self._sessions.get(session_id)

        if action in [Action.REMOVE, Action.START]:
            payload["session_id"] = session_id

        client = self._client()

        assert client, "Client should be garbage collected, but it is not"

        await client.send_event(
            EventMessage(
                kind=ServerEvent.SESSIONS_UPDATE,
                payload=payload,
            )
        )

    async def handle(self, client: Client, event: EventMessage) -> None:
        match event:
            case EventMessage(kind=ClientEvent.SESSIONS_SUBSCRIBE):
                self._sessions.subscribe(client.id, self._session_observer)
            case EventMessage(kind=ClientEvent.SESSIONS_UNSUBSCRIBE):
                self._sessions.unsubscribe(client.id)
