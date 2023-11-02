import asyncio
import weakref
from dataclasses import asdict
from typing import Any, Collection

from battleship.engine import domain
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
        self.clients = (client_a, client_b)
        self.player_a = domain.Player(client_a.user.nickname)
        self.player_b = domain.Player(client_b.user.nickname)
        self.player = {client_a.id: self.player_a, client_b.id: self.player_b}
        self.roster = get_roster(session.roster)
        self.game = domain.Game(
            self.player_a,
            self.player_b,
            self.roster,
            session.firing_order,  # type: ignore
            session.salvo_mode,
        )
        self.players_ready = 0

    def broadcast(self, event: EventMessage) -> None:
        for client in self.clients:
            asyncio.create_task(client.send_event(event))

    def send_awaiting_move(self) -> None:
        payload = dict(
            actor=self.game.current_player.name, subject=self.game.player_under_attack.name
        )

        self.broadcast(
            EventMessage(
                kind=ServerEvent.AWAITING_MOVE,
                payload=payload,
            )
        )

    def send_fleet_ready(self, player_name: str) -> None:
        self.broadcast(EventMessage(kind=ServerEvent.FLEET_READY, payload=dict(player=player_name)))

    def send_salvo(self, salvo: domain.Salvo) -> None:
        model = salvo_to_model(salvo)
        event = EventMessage(kind=ServerEvent.SALVO, payload=dict(salvo=model.to_json()))
        self.broadcast(event)

    async def __call__(self) -> None:
        await self.client_a.send_event(
            EventMessage(
                kind=ServerEvent.START_GAME,
                payload=dict(enemy=self.client_b.user.nickname, roster=asdict(self.roster)),
            )
        )
        await self.client_b.send_event(
            EventMessage(
                kind=ServerEvent.START_GAME,
                payload=dict(enemy=self.client_a.user.nickname, roster=asdict(self.roster)),
            )
        )

    async def handle(self, client: Client, event: EventMessage) -> None:
        match event:
            case EventMessage(kind=ClientEvent.SPAWN_SHIP):
                ship_id: str = event.payload["ship_id"]
                position: Collection[str] = event.payload["position"]
                player = self.player[client.id]
                self.game.add_ship(player, position, ship_id)

                await client.send_event(
                    EventMessage(kind=ServerEvent.SHIP_SPAWNED, payload=event.payload.copy())
                )

                if self.game.is_fleet_ready(player):
                    self.send_fleet_ready(player.name)

                    self.players_ready += 1

                    if self.players_ready == 2:
                        self.game.start()
                        self.send_awaiting_move()
            case EventMessage(kind=ClientEvent.FIRE):
                position = event.payload["position"]
                salvo = self.game.fire(position)
                self.send_salvo(salvo)

                if self.game.winner:
                    self.broadcast(
                        EventMessage(
                            kind=ServerEvent.GAME_ENDED, payload=dict(winner=self.game.winner.name)
                        )
                    )
                else:
                    self.send_awaiting_move()


class SessionSubscriptionHandler(EventHandler):
    def __init__(self, client: Client, session_repository: Sessions) -> None:
        self._client = weakref.ref(client)
        self._sessions = session_repository

    async def _session_observer(self, session_id: str, action: Action) -> None:
        logger.info(f"Session {session_id}, action {action.value}.")
        payload: dict[str, Any] = dict(action=action)

        if action == Action.ADD:
            payload["session"] = self._sessions.get(session_id)

        if action == Action.REMOVE:
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
