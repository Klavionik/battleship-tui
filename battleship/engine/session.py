from typing import Collection

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

    def spawn_bot_fleet(self) -> None:
        for ship_type, _ in self.roster:
            position = self.autoplacer.place(ship_type)
            self._game.add_ship(self.bot, position, ship_type)

    def fire(self, coordinates: Collection[str]) -> list[domain.Shot]:
        return self._game.fire(coordinates)
