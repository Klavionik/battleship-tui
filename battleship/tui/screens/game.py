from datetime import datetime
from string import Template
from typing import Any, Iterable

from textual import on
from textual.app import DEFAULT_COLORS, ComposeResult
from textual.containers import Grid
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import Footer

from battleship.engine import domain
from battleship.shared import models
from battleship.tui import screens, strategies
from battleship.tui.widgets.announcement import (
    PHASE_BATTLE,
    PHASE_BATTLE_SALVO,
    PHASE_DEFEAT,
    PHASE_VICTORY,
    RULES_TEMPLATE,
    Announcement,
)
from battleship.tui.widgets.battle_log import BattleLog
from battleship.tui.widgets.board import Board, CellFactory
from battleship.tui.widgets.fleet import Fleet, Ship


def convert_to_coordinate(coordinate: Coordinate) -> str:
    return chr(coordinate.column + 1 + 64) + str(coordinate.row + 1)


def convert_from_coordinate(coordinate: str) -> Coordinate:
    column, row = domain.parse_coordinate(coordinate)
    return Coordinate(row - 1, ord(column) - 1 - 64)


class Game(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(
        self,
        *args: Any,
        game: domain.Game,
        strategy: strategies.GameStrategy,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._game = game
        self._strategy = strategy

        dark_theme = DEFAULT_COLORS.get("dark")
        assert dark_theme
        colors = dark_theme.generate()

        self._player_name = game.player_a.name
        self._enemy_name = game.player_b.name

        player_cell_factory = CellFactory(ship_bg=colors["success-darken-1"])
        enemy_cell_factory = CellFactory(ship_bg=colors["accent-darken-1"])

        self.player_board = Board(
            player_name=game.player_a.name,
            size=domain.DEFAULT_BOARD_SIZE,
            cell_factory=player_cell_factory,
            classes="player",
        )
        self.enemy_board = Board(
            player_name=game.player_b.name,
            size=domain.DEFAULT_BOARD_SIZE,
            cell_factory=enemy_cell_factory,
            classes="enemy",
        )

        self.player_fleet = Fleet(
            roster=game.roster,
            cell_factory=player_cell_factory,
            classes="player",
        )
        self.player_fleet.border_title = "Your fleet"
        self.enemy_fleet = Fleet(
            roster=game.roster,
            cell_factory=enemy_cell_factory,
            allow_placing=False,
            classes="enemy",
        )
        self.enemy_fleet.border_title = "Enemy fleet"

        self.board_map = {
            self._player_name: self.player_board,
            self._enemy_name: self.enemy_board,
        }
        self.fleet_map = {
            self._player_name: self.player_fleet,
            self._enemy_name: self.enemy_fleet,
        }
        self.players_ready = 0

        if game.salvo_mode:
            self.enemy_board.min_targets = len(game.roster)

        self.battle_log = BattleLog()

        self.announcement = Announcement(rules=self._format_rules(RULES_TEMPLATE))

        self._strategy.subscribe("fleet_ready", self.on_fleet_ready)
        self._strategy.subscribe("ship_spawned", self.on_ship_spawned)
        self._strategy.subscribe("awaiting_move", self.on_awaiting_move)
        self._strategy.subscribe("salvo", self.on_salvo)
        self._strategy.subscribe("game_ended", self.on_game_ended)

    def compose(self) -> ComposeResult:
        with Grid(id="content"):
            yield self.player_board
            yield self.announcement
            yield self.enemy_board
            yield self.player_fleet
            yield self.battle_log
            yield self.enemy_fleet

        yield Footer()

    def write_as_game(self, text: str) -> None:
        now = datetime.now().strftime("%H:%M")
        time = f"[cyan]{now}[/]"
        prefix = "[yellow][Game][/]:"
        self.battle_log.write(f"{time} {prefix} {text}")

    @on(Board.ShipPlaced)
    def spawn_ship(self, event: Board.ShipPlaced) -> None:
        self.player_board.mode = Board.Mode.DISPLAY
        position = [convert_to_coordinate(c) for c in event.coordinates]
        self._strategy.spawn_ship(ship_id=event.ship.id, position=position)

    def on_fleet_ready(self, player: str) -> None:
        self.write_as_game(f"{player}'s fleet is ready")
        self.players_ready += 1

        if self.players_ready == 2:
            text = PHASE_BATTLE_SALVO if self._game.salvo_mode else PHASE_BATTLE
            self.query_one(Announcement).update_phase(text)

    def on_awaiting_move(self, actor: str, subject: str) -> None:
        self.board_map[actor].mode = Board.Mode.DISPLAY

        if (subject_board := self.board_map[subject]) != self.player_board:
            subject_board.mode = Board.Mode.TARGET

        self.write_as_game(f"{actor}'s turn. Fire at will!")

    def on_ship_spawned(self, player: str, ship_id: str, position: Iterable[str]) -> None:
        self.board_map[player].paint_ship([convert_from_coordinate(p) for p in position])
        self.fleet_map[player].place(ship_id)

    def on_salvo(self, salvo: models.Salvo) -> None:
        board = self.board_map[salvo.subject.name]
        fleet = self.fleet_map[salvo.subject.name]

        for shot in salvo.shots:
            coor = convert_from_coordinate(shot.coordinate)

            if shot.miss:
                board.paint_miss(coor)
                result = "Miss"
            else:
                assert shot.ship, "Shot was a hit, but no ship"

                if shot.ship.destroyed:
                    status = "sunk"
                    board.paint_destroyed(map(convert_from_coordinate, shot.ship.cells))
                else:
                    status = "hit"
                    board.paint_damage(coor)

                fleet.damage(shot.ship.id)
                result = f"{shot.ship.type.title()} {status}"

            self.write_as_game(f"{salvo.actor.name} attacks {shot.coordinate}. {result}")

        if self._game.salvo_mode:
            self.board_map[salvo.actor.name].min_targets = salvo.ships_left

    def on_game_ended(self, winner: str) -> None:
        for board in self.board_map.values():
            board.mode = Board.Mode.DISPLAY

        self.write_as_game(f"{winner} has won!")

        text = PHASE_VICTORY if self._game.player_a.name == winner else PHASE_DEFEAT
        self.query_one(Announcement).update_phase(text)

    @on(Board.CellShot)
    def fire(self, event: Board.CellShot) -> None:
        self.enemy_board.mode = Board.Mode.DISPLAY
        position = [convert_to_coordinate(c) for c in event.coordinates]
        self._strategy.fire(position=position)

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Ship.ShowPreview)
    def show_ship_preview(self, event: Ship.ShowPreview) -> None:
        self.player_board.mode = Board.Mode.ARRANGE
        roster_item = self._game.roster[event.ship_key]
        self.player_board.show_ship_preview(ship_id=roster_item.id, ship_hp=roster_item.hp)

    def _format_rules(self, template: str) -> str:
        salvo_mode = "Yes" if self._game.salvo_mode else "No"
        firing_order = self._game.firing_order.replace("_", " ").capitalize()
        return Template(template).substitute(
            salvo_mode=salvo_mode,
            firing_order=firing_order,
            roster=self._game.roster.name.capitalize(),
        )
