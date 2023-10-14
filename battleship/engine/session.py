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
        self.player = domain.Player(player_name)
        self.bot = domain.Player("Computer")
        self.roster = roster
        self.firing_order = firing_order
        self.salvo_mode = salvo_mode
        self.target_caller = ai.TargetCaller(self.player.board)
        self.autoplacer = ai.Autoplacer(self.bot.board, self.roster)
        self._game = self.create_game()
        self.ships_to_place = list(reversed(self.roster))
        self.ee = AsyncIOEventEmitter()

        self.ee.add_listener("spawn_ship", self.spawn_ship)
        self.ee.add_listener("fire", self.fire)

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        self.ee.add_listener(event, handler)

    def notify(self, event: str, *args: Any, **kwargs: Any) -> None:
        self.ee.emit(event, *args, **kwargs)

    def create_game(self) -> domain.Game:
        game = domain.Game(
            player_a=self.player,
            player_b=self.bot,
            roster=self.roster,
            firing_order=self.firing_order,
            salvo_mode=self.salvo_mode,
        )
        return game

    @property
    def player_name(self) -> str:
        return self.player.name

    @property
    def bot_name(self) -> str:
        return self.bot.name

    def spawn_ship(self, position: Collection[str], ship_type: str) -> None:
        self._game.add_ship(self.player, position, ship_type)
        self.ee.emit("ship_spawned", position=position)

        if self._game.is_fleet_ready(self.player):
            self.ee.emit("fleet_ready", player=self.player)
            self._game.start()

            if self._game.current_player is self.bot:
                self.make_bot_move()
            else:
                self.ee.emit(
                    "awaiting_move",
                    actor=self._game.current_player,
                    subject=self._game.player_under_attack,
                )
        else:
            self._request_ship_position()

    def spawn_bot_fleet(self) -> None:
        for ship_type, _ in self.roster:
            position = self.autoplacer.place(ship_type)
            self._game.add_ship(self.bot, position, ship_type)

        self.ee.emit("fleet_ready", player=self.bot)

    def make_bot_move(self) -> None:
        if self.salvo_mode:
            count = self.bot.ships_alive
        else:
            count = 1
        target = self.target_caller.call_out(count=count)

        self.fire(target)

    def fire(self, position: Collection[str]) -> None:
        actor = self._game.current_player
        salvo = self._game.fire(position)
        self.ee.emit("salvo", salvo=salvo)

        if self._game.ended:
            self.ee.emit("game_ended", winner=self._game.winner)
            return

        if actor is self.bot:
            self.target_caller.provide_feedback(salvo)

        if self._game.current_player is self.bot:
            self.make_bot_move()
        else:
            self.ee.emit(
                "awaiting_move",
                actor=self._game.current_player,
                subject=self._game.player_under_attack,
            )

    def _request_ship_position(self) -> None:
        ship = self.ships_to_place.pop()
        self.ee.emit("request_ship_position", hp=ship.hp, ship_type=ship.type)

    def start(self) -> None:
        self.spawn_bot_fleet()
        self._request_ship_position()
