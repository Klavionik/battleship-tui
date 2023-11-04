import abc
from asyncio import create_task
from typing import Any, Callable, Collection

from pyee.asyncio import AsyncIOEventEmitter

from battleship.client import Client
from battleship.engine import ai, domain
from battleship.shared import models
from battleship.shared.events import ServerEvent

__all__ = ["GameStrategy", "SingleplayerStrategy", "MultiplayerStrategy"]


class GameStrategy(abc.ABC):
    def __init__(self) -> None:
        self._ee = AsyncIOEventEmitter()

    @abc.abstractmethod
    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        pass

    @abc.abstractmethod
    def fire(self, position: Collection[str]) -> None:
        pass

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        self._ee.add_listener(event, handler)

    def emit_ship_spawned(self, player: str, ship_id: str, position: Collection[str]) -> None:
        self._ee.emit("ship_spawned", player=player, ship_id=ship_id, position=position)

    def emit_fleet_ready(self, player: str) -> None:
        self._ee.emit("fleet_ready", player=player)

    def emit_awaiting_move(self, actor: str, subject: str) -> None:
        self._ee.emit("awaiting_move", actor=actor, subject=subject)

    def emit_salvo(self, salvo: models.Salvo) -> None:
        self._ee.emit("salvo", salvo=salvo)

    def emit_game_ended(self, winner: str) -> None:
        self._ee.emit("game_ended", winner=winner)


class MultiplayerStrategy(GameStrategy):
    def __init__(self, client: Client):
        super().__init__()
        self._client = client

        client.add_listener(ServerEvent.SHIP_SPAWNED, self._on_ship_spawned)
        client.add_listener(ServerEvent.FLEET_READY, self._on_fleet_ready)
        client.add_listener(ServerEvent.AWAITING_MOVE, self._on_awaiting_move)
        client.add_listener(ServerEvent.SALVO, self._on_salvo)
        client.add_listener(ServerEvent.GAME_ENDED, self._on_game_ended)

    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        create_task(self._client.spawn_ship(ship_id, position))

    def fire(self, position: Collection[str]) -> None:
        create_task(self._client.fire(position))

    def _on_ship_spawned(self, payload: dict[str, Any]) -> None:
        player = payload["player"]
        ship_id = payload["ship_id"]
        position = payload["position"]
        self.emit_ship_spawned(player, ship_id, position)

    def _on_fleet_ready(self, payload: dict[str, Any]) -> None:
        player = payload["player"]
        self.emit_fleet_ready(player)

    def _on_awaiting_move(self, payload: dict[str, Any]) -> None:
        actor = payload["actor"]
        subject = payload["subject"]
        self.emit_awaiting_move(actor, subject)

    def _on_salvo(self, payload: dict[str, Any]) -> None:
        salvo = models.Salvo.from_raw(payload["salvo"])
        self.emit_salvo(salvo)

    def _on_game_ended(self, payload: dict[str, Any]) -> None:
        winner = payload["winner"]
        self.emit_game_ended(winner)


class SingleplayerStrategy(GameStrategy):
    def __init__(self, game: domain.Game):
        super().__init__()
        self._game = game
        self._human_player = game.player_a
        self._bot_player = game.player_b
        self._target_caller = ai.TargetCaller(self._human_player.board)
        self._autoplacer = ai.Autoplacer(self._bot_player.board, self._game.roster)

        game.register_hook(domain.Hook.SHIP_ADDED, self._ship_added_hook)
        game.register_hook(domain.Hook.FLEET_READY, self._fleet_ready_hook)
        game.register_hook(domain.Hook.NEXT_MOVE, self._next_move_hook)
        game.register_hook(domain.Hook.GAME_ENDED, self._game_ended_hook)

    def _next_move_hook(self, game: domain.Game) -> None:
        self.emit_awaiting_move(
            actor=game.current_player.name, subject=game.player_under_attack.name
        )

        if game.current_player is self._bot_player:
            target = self._call_bot_target()
            self.fire(target)

    def _game_ended_hook(self, game: domain.Game) -> None:
        assert game.winner
        self.emit_game_ended(game.winner.name)

    def _ship_added_hook(
        self,
        player: domain.Player,
        ship_id: str,
        position: Collection[str],
    ) -> None:
        if player is self._human_player:
            self.emit_ship_spawned(player.name, ship_id, position)

    def _fleet_ready_hook(self, player: domain.Player) -> None:
        self.emit_fleet_ready(player.name)

        if player is self._human_player:
            self._spawn_bot_fleet()

    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        self._game.add_ship(self._game.player_a, position, ship_id)

    def fire(self, position: Collection[str]) -> None:
        salvo = self._game.fire(position)
        self.emit_salvo(models.salvo_to_model(salvo))

        if salvo.actor is self._bot_player:
            self._target_caller.provide_feedback(salvo.shots)

        self._game.turn(salvo)

    def _call_bot_target(self) -> Collection[str]:
        if self._game.salvo_mode:
            count = self._bot_player.ships_alive
        else:
            count = 1

        position = self._target_caller.call_out(count=count)
        return position

    def _spawn_bot_fleet(self) -> None:
        for item in self._game.roster:
            position = self._autoplacer.place(item.type)
            self._game.add_ship(self._bot_player, position, item.id)
