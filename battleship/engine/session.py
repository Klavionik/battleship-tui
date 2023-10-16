from typing import Any, Callable, Collection

from pyee.asyncio import AsyncIOEventEmitter

from battleship.engine import ai, domain, roster


class SingleplayerSession:
    def __init__(
        self,
        player_name: str,
        roster: roster.Roster,
        firing_order: domain.FiringOrder,
        salvo_mode: bool = False,
    ):
        self._player = domain.Player(player_name)
        self._enemy = domain.Player("Computer")
        self._roster = roster
        self._firing_order = firing_order
        self._salvo_mode = salvo_mode
        self._target_caller = ai.TargetCaller(self._player.board)
        self._autoplacer = ai.Autoplacer(self._enemy.board, self._roster)
        self._game = self._create_game()
        self._ships_to_place = list(reversed(self._roster))
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
        self._request_ship_position()

    def _create_game(self) -> domain.Game:
        game = domain.Game(
            player_a=self._player,
            player_b=self._enemy,
            roster=self._roster,
            firing_order=self._firing_order,
            salvo_mode=self.salvo_mode,
        )
        return game

    def _spawn_ship(self, position: Collection[str], ship_type: str) -> None:
        self._game.add_ship(self._player, position, ship_type)
        self._ee.emit("ship_spawned", position=position)

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
        else:
            self._request_ship_position()

    def _spawn_enemy_fleet(self) -> None:
        for ship_type, _ in self._roster:
            position = self._autoplacer.place(ship_type)
            self._game.add_ship(self._enemy, position, ship_type)

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

    def _request_ship_position(self) -> None:
        ship = self._ships_to_place.pop()
        self._ee.emit("request_ship_position", hp=ship.hp, ship_type=ship.type)
