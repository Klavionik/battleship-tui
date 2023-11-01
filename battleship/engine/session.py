import abc
from typing import Any, Callable, Collection

from pyee.asyncio import AsyncIOEventEmitter

from battleship.engine import ai, domain, roster


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
    def notify(self, event: str, *args: Any, **kwargs: Any) -> None:
        pass

    @abc.abstractmethod
    def start(self) -> None:
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
        self._ships_to_place = list(self._roster)
        self._ee = AsyncIOEventEmitter()

        self._ee.add_listener("spawn_ship", self._spawn_ship)
        self._ee.add_listener("fire", self._fire)

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

    def notify(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._ee.emit(event, *args, **kwargs)

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

    def _spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        item = self.roster[ship_id]
        self._game.add_ship(self._player, position, item.id)
        self._ee.emit("ship_spawned", ship_id=ship_id, position=position)

        if self._game.is_fleet_ready(self._player):
            self._ee.emit("fleet_ready", player=self._player)
            self._game.start()

            if self._game.current_player is self._enemy:
                self._make_enemy_move()
            else:
                self._ee.emit(
                    "awaiting_move",
                    actor=self._game.current_player,
                    subject=self._game.player_under_attack,
                )

    def _spawn_enemy_fleet(self) -> None:
        for item in self._roster:
            position = self._autoplacer.place(item.type)
            self._game.add_ship(self._enemy, position, item.id)

        self._ee.emit("fleet_ready", player=self._enemy)

    def _make_enemy_move(self) -> None:
        if self.salvo_mode:
            count = self._enemy.ships_alive
        else:
            count = 1
        target = self._target_caller.call_out(count=count)

        self._fire(target)

    def _fire(self, position: Collection[str]) -> None:
        actor = self._game.current_player
        salvo = self._game.fire(position)
        self._ee.emit("salvo", salvo=salvo)

        if self._game.ended:
            self._ee.emit("game_ended", winner=self._game.winner)
            return

        if actor is self._enemy:
            self._target_caller.provide_feedback(salvo)

        if self._game.current_player is self._enemy:
            self._make_enemy_move()
        else:
            self._ee.emit(
                "awaiting_move",
                actor=self._game.current_player,
                subject=self._game.player_under_attack,
            )


class MultiplayerSession(Session):
    def __init__(
        self,
        player_name: str,
        enemy_name: str,
        roster_name: str,
        firing_order: str,
        salvo_mode: bool = False,
    ):
        self._player = domain.Player(player_name)
        self._enemy = domain.Player(enemy_name)
        self._roster = roster.get_roster(roster_name)
        self._firing_order = firing_order
        self._salvo_mode = salvo_mode
        self._target_caller = ai.TargetCaller(self._player.board)
        self._autoplacer = ai.Autoplacer(self._enemy.board, self._roster)
        self._game = self._create_game()
        self._ships_to_place = list(self._roster)
        self._ee = AsyncIOEventEmitter()

        self._ee.add_listener("spawn_ship", self._spawn_ship)
        self._ee.add_listener("fire", self._fire)

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

    def notify(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._ee.emit(event, *args, **kwargs)

    def start(self) -> None:
        self._spawn_enemy_fleet()

    def _create_game(self) -> domain.Game:
        game = domain.Game(
            player_a=self._player,
            player_b=self._enemy,
            roster=self._roster,
            firing_order=self._firing_order,  # type: ignore
            salvo_mode=self.salvo_mode,
        )
        return game

    def _spawn_ship(self, ship_id: str, position: Collection[str]) -> None:
        item = self.roster[ship_id]
        self._game.add_ship(self._player, position, item.id)
        self._ee.emit("ship_spawned", ship_id=ship_id, position=position)

        if self._game.is_fleet_ready(self._player):
            self._ee.emit("fleet_ready", player=self._player)
            self._game.start()

            if self._game.current_player is self._enemy:
                self._make_enemy_move()
            else:
                self._ee.emit(
                    "awaiting_move",
                    actor=self._game.current_player,
                    subject=self._game.player_under_attack,
                )

    def _spawn_enemy_fleet(self) -> None:
        for item in self._roster:
            position = self._autoplacer.place(item.type)
            self._game.add_ship(self._enemy, position, item.id)

        self._ee.emit("fleet_ready", player=self._enemy)

    def _make_enemy_move(self) -> None:
        if self.salvo_mode:
            count = self._enemy.ships_alive
        else:
            count = 1
        target = self._target_caller.call_out(count=count)

        self._fire(target)

    def _fire(self, position: Collection[str]) -> None:
        actor = self._game.current_player
        salvo = self._game.fire(position)
        self._ee.emit("salvo", salvo=salvo)

        if self._game.ended:
            self._ee.emit("game_ended", winner=self._game.winner)
            return

        if actor is self._enemy:
            self._target_caller.provide_feedback(salvo)

        if self._game.current_player is self._enemy:
            self._make_enemy_move()
        else:
            self._ee.emit(
                "awaiting_move",
                actor=self._game.current_player,
                subject=self._game.player_under_attack,
            )
