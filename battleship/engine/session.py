import abc
from asyncio import create_task
from typing import Any, Callable, Collection

from pyee.asyncio import AsyncIOEventEmitter

from battleship.client import Client
from battleship.engine import ai, domain, roster
from battleship.shared import models
from battleship.shared.events import ServerEvent


class Session(abc.ABC):
    @property
    @abc.abstractmethod
    def player_name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def enemy_name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def firing_order(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def salvo_mode(self) -> bool:
        pass

    @property
    @abc.abstractmethod
    def roster(self) -> roster.Roster:
        pass

    @abc.abstractmethod
    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        pass

    @abc.abstractmethod
    def start(self) -> None:
        pass

    @abc.abstractmethod
    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        pass

    @abc.abstractmethod
    def fire(self, position: Collection[str]) -> None:
        pass


class SingleplayerSession(Session):
    def __init__(
        self,
        player_name: str,
        roster_name: str,
        firing_order: domain.FiringOrder,
        salvo_mode: bool = False,
    ):
        self._player = domain.Player(player_name)
        self._enemy = domain.Player("Computer")
        self._roster = roster.get_roster(roster_name)
        self._firing_order = firing_order
        self._salvo_mode = salvo_mode
        self._target_caller = ai.TargetCaller(self._player.board)
        self._autoplacer = ai.Autoplacer(self._enemy.board, self._roster)
        self._game = self._create_game()
        self._ee = AsyncIOEventEmitter()

    @property
    def player_name(self) -> str:
        return self._player.name

    @property
    def enemy_name(self) -> str:
        return self._enemy.name

    @property
    def firing_order(self) -> str:
        return self._firing_order

    @property
    def salvo_mode(self) -> bool:
        return self._salvo_mode

    @property
    def roster(self) -> roster.Roster:
        return self._roster

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        self._ee.add_listener(event, handler)

    def start(self) -> None:
        self._spawn_enemy_fleet()

    def _create_game(self) -> domain.Game:
        game = domain.Game(
            player_a=self._player,
            player_b=self._enemy,
            roster=self._roster,
            firing_order=self._firing_order,
            salvo_mode=self.salvo_mode,
        )
        return game

    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        item = self.roster[ship_id]
        self._game.add_ship(self._player, position, item.id)
        self._ee.emit("ship_spawned", ship_id=ship_id, position=position)

        if self._game.is_fleet_ready(self._player):
            self._ee.emit("fleet_ready", player=self._player.name)
            self._game.start()

            if self._game.current_player is self._enemy:
                self._make_enemy_move()
            else:
                self._ee.emit(
                    "awaiting_move",
                    actor=self._game.current_player.name,
                    subject=self._game.player_under_attack.name,
                )

    def _spawn_enemy_fleet(self) -> None:
        for item in self._roster:
            position = self._autoplacer.place(item.type)
            self._game.add_ship(self._enemy, position, item.id)

        self._ee.emit("fleet_ready", player=self._enemy.name)

    def _make_enemy_move(self) -> None:
        if self.salvo_mode:
            count = self._enemy.ships_alive
        else:
            count = 1
        target = self._target_caller.call_out(count=count)

        self.fire(target)

    def fire(self, position: Collection[str]) -> None:
        actor = self._game.current_player
        salvo = self._game.fire(position)
        self._ee.emit("salvo", salvo=salvo)

        if self._game.winner:
            self._ee.emit("game_ended", winner=self._game.winner.name)
            return

        if actor is self._enemy:
            self._target_caller.provide_feedback(salvo)

        if self._game.current_player is self._enemy:
            self._make_enemy_move()
        else:
            self._ee.emit(
                "awaiting_move",
                actor=self._game.current_player.name,
                subject=self._game.player_under_attack.name,
            )


class MultiplayerSession(Session):
    def __init__(
        self,
        client: Client,
        player_name: str,
        enemy_name: str,
        roster: roster.Roster,
        firing_order: str,
        salvo_mode: bool = False,
    ):
        self._player = player_name
        self._enemy = enemy_name
        self._roster = roster
        self._firing_order = firing_order
        self._salvo_mode = salvo_mode
        self._ee = AsyncIOEventEmitter()
        self._client = client

        client.add_listener(ServerEvent.SHIP_SPAWNED, self._on_ship_spawned)
        client.add_listener(ServerEvent.FLEET_READY, self._on_fleet_ready)
        client.add_listener(ServerEvent.AWAITING_MOVE, self._on_awaiting_move)
        client.add_listener(ServerEvent.SALVO, self._on_salvo)
        client.add_listener(ServerEvent.GAME_ENDED, self._on_game_ended)

    @property
    def player_name(self) -> str:
        return self._player

    @property
    def enemy_name(self) -> str:
        return self._enemy

    @property
    def firing_order(self) -> str:
        return self._firing_order

    @property
    def salvo_mode(self) -> bool:
        return self._salvo_mode

    @property
    def roster(self) -> roster.Roster:
        return self._roster

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        self._ee.add_listener(event, handler)

    def start(self) -> None:
        pass

    def _on_ship_spawned(self, payload: dict[str, Any]) -> None:
        ship_id = payload["ship_id"]
        position = payload["position"]
        self._ee.emit("ship_spawned", ship_id=ship_id, position=position)

    def _on_fleet_ready(self, payload: dict[str, Any]) -> None:
        player = payload["player"]
        self._ee.emit("fleet_ready", player=player)

    def _on_awaiting_move(self, payload: dict[str, Any]) -> None:
        actor = payload["actor"]
        subject = payload["subject"]

        self._ee.emit("awaiting_move", actor=actor, subject=subject)

    def _on_salvo(self, payload: dict[str, Any]) -> None:
        salvo = models.Salvo.from_raw(payload["salvo"])
        self._ee.emit("salvo", salvo=salvo)

    def _on_game_ended(self, payload: dict[str, Any]) -> None:
        winner = payload["winner"]
        self._ee.emit("game_ended", winner=winner)

    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        create_task(self._client.spawn_ship(ship_id, position))

    def fire(self, position: Collection[str]) -> None:
        create_task(self._client.fire(position))
