import abc
from asyncio import create_task
from time import time
from typing import Any, Callable, Collection

from pyee.asyncio import AsyncIOEventEmitter

from battleship.client import Client
from battleship.engine import Roster, ai, domain
from battleship.shared import models
from battleship.shared.events import ServerEvent

__all__ = ["GameStrategy", "SingleplayerStrategy", "MultiplayerStrategy"]


class GameStrategy(abc.ABC):
    def __init__(self) -> None:
        self._ee = AsyncIOEventEmitter()

    @property
    @abc.abstractmethod
    def player(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def enemy(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def roster(self) -> Roster:
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
    def winner(self) -> str | None:
        pass

    @abc.abstractmethod
    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        pass

    @abc.abstractmethod
    def fire(self, position: Collection[str]) -> None:
        pass

    @abc.abstractmethod
    def cancel(self) -> None:
        pass

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        self._ee.add_listener(event, handler)

    def unsubscribe(self) -> None:
        self._ee.remove_all_listeners()

    def emit_ship_spawned(self, player: str, ship_id: str, position: Collection[str]) -> None:
        self._ee.emit("ship_spawned", player=player, ship_id=ship_id, position=position)

    def emit_fleet_ready(self, player: str) -> None:
        self._ee.emit("fleet_ready", player=player)

    def emit_awaiting_move(self, actor: str, subject: str) -> None:
        self._ee.emit("awaiting_move", actor=actor, subject=subject)

    def emit_salvo(self, salvo: models.Salvo) -> None:
        self._ee.emit("salvo", salvo=salvo)

    def emit_game_ended(self, winner: str, summary: models.GameSummary) -> None:
        self._ee.emit("game_ended", winner=winner, summary=summary)


class MultiplayerStrategy(GameStrategy):
    def __init__(
        self,
        player: str,
        enemy: str,
        roster: Roster,
        firing_order: str,
        salvo_mode: bool,
        client: Client,
    ):
        super().__init__()
        self._player = player
        self._enemy = enemy
        self._roster = roster
        self._firing_order = firing_order
        self._salvo_mode = salvo_mode
        self._winner = None
        self._client = client

        client.add_listener(ServerEvent.SHIP_SPAWNED, self._on_ship_spawned)
        client.add_listener(ServerEvent.FLEET_READY, self._on_fleet_ready)
        client.add_listener(ServerEvent.AWAITING_MOVE, self._on_awaiting_move)
        client.add_listener(ServerEvent.SALVO, self._on_salvo)
        client.add_listener(ServerEvent.GAME_ENDED, self._on_game_ended)
        client.add_listener(ServerEvent.GAME_CANCELLED, self._on_game_cancelled)

    @property
    def player(self) -> str:
        return self._player

    @property
    def enemy(self) -> str:
        return self._enemy

    @property
    def roster(self) -> Roster:
        return self._roster

    @property
    def firing_order(self) -> str:
        return self._firing_order

    @property
    def salvo_mode(self) -> bool:
        return self._salvo_mode

    @property
    def winner(self) -> str | None:
        return self._winner

    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        create_task(self._client.spawn_ship(ship_id, position))

    def fire(self, position: Collection[str]) -> None:
        create_task(self._client.fire(position))

    def cancel(self) -> None:
        create_task(self._client.cancel_game())

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
        self._winner = winner
        summary = models.GameSummary.from_raw(payload["summary"])
        self.emit_game_ended(winner, summary)

    def _on_game_cancelled(self, payload: dict[str, Any]) -> None:
        reason = payload["reason"]
        self._ee.emit("game_cancelled", reason=reason)


class SingleplayerStrategy(GameStrategy):
    def __init__(self, game: domain.Game):
        super().__init__()
        self._game = game
        self._human_player = game.player_a
        self._bot_player = game.player_b
        self._target_caller = ai.TargetCaller(self._human_player.board)
        self._autoplacer = ai.Autoplacer(self._bot_player.board, self._game.roster)
        self._start = time()
        self._summary = models.GameSummary()

        self._spawn_bot_fleet()

        game.register_hook(domain.Hook.SHIP_ADDED, self._ship_added_hook)
        game.register_hook(domain.Hook.FLEET_READY, self._fleet_ready_hook)
        game.register_hook(domain.Hook.NEXT_MOVE, self._next_move_hook)
        game.register_hook(domain.Hook.GAME_ENDED, self._game_ended_hook)

    @property
    def player(self) -> str:
        return self._human_player.name

    @property
    def enemy(self) -> str:
        return self._bot_player.name

    @property
    def roster(self) -> Roster:
        return self._game.roster

    @property
    def firing_order(self) -> str:
        return self._game.firing_order

    @property
    def salvo_mode(self) -> bool:
        return self._game.salvo_mode

    @property
    def winner(self) -> str | None:
        if self._game.winner:
            return self._game.winner.name

    def _next_move_hook(self, game: domain.Game) -> None:
        self.emit_awaiting_move(
            actor=game.current_player.name, subject=game.player_under_attack.name
        )

        if game.current_player is self._bot_player:
            target = self._call_bot_target()
            self.fire(target)

    def _game_ended_hook(self, game: domain.Game) -> None:
        assert game.winner
        self._summary.finalize(game.winner, start=self._start, end=time())
        self.emit_game_ended(game.winner.name, self._summary)

    def _ship_added_hook(
        self,
        player: domain.Player,
        ship_id: str,
        position: Collection[str],
    ) -> None:
        self.emit_ship_spawned(player.name, ship_id, position)

    def _fleet_ready_hook(self, player: domain.Player) -> None:
        self.emit_fleet_ready(player.name)

        # When player's fleet is ready, emit ready for bot fleet.
        self.emit_fleet_ready(self._bot_player.name)

    def spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        self._game.add_ship(self._game.player_a, position, ship_id)

    def fire(self, position: Collection[str]) -> None:
        salvo = self._game.fire(position)
        self._summary.update_shots(salvo)
        self.emit_salvo(models.salvo_to_model(salvo))

        if salvo.actor is self._bot_player:
            self._target_caller.provide_feedback(salvo.shots)

        self._game.turn(salvo)

    def cancel(self) -> None:
        pass

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
