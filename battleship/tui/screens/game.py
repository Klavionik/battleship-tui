from datetime import datetime
from string import Template
from typing import Any, Iterable, Literal

import inject
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.coordinate import Coordinate
from textual.screen import Screen

from battleship.engine import domain
from battleship.shared import models
from battleship.tui import strategies
from battleship.tui.settings import SettingsProvider
from battleship.tui.widgets import AppFooter
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
from battleship.tui.widgets.modals import GameSummaryModal, SessionEndModal


def convert_to_coordinate(coordinate: Coordinate) -> str:
    return chr(coordinate.column + 1 + 64) + str(coordinate.row + 1)


def convert_from_coordinate(coordinate: str) -> Coordinate:
    column, row = domain.parse_coordinate(coordinate)
    return Coordinate(row - 1, ord(column) - 1 - 64)


CANCEL_MSG = {
    "quit": "%s has quit the game",
    "disconnect": "%s disconnected from the server",
    "error": "An error occured during the game",
}


class Game(Screen[None]):
    BINDINGS = [("escape", "back", "Back"), ("ctrl+q", "try_quit", "Quit")]

    @inject.param("settings_provider", SettingsProvider)
    def __init__(
        self,
        *args: Any,
        strategy: strategies.GameStrategy,
        settings_provider: SettingsProvider,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._settings = settings_provider.load()
        self._strategy = strategy

        self._player_name = strategy.player
        self._enemy_name = strategy.enemy

        player_cell_factory = CellFactory(ship_bg=self._settings.fleet_color)
        enemy_cell_factory = CellFactory(ship_bg=self._settings.enemy_fleet_color)

        self.player_board = Board(
            player_name=strategy.player,
            size=domain.DEFAULT_BOARD_SIZE,
            cell_factory=player_cell_factory,
            classes="player",
        )
        self.enemy_board = Board(
            player_name=strategy.enemy,
            size=domain.DEFAULT_BOARD_SIZE,
            cell_factory=enemy_cell_factory,
            classes="enemy",
        )

        self.player_fleet = Fleet(
            id="player_fleet",
            roster=strategy.roster,
            cell_factory=player_cell_factory,
            classes="player",
        )
        self.player_fleet.border_title = "Your fleet"
        self.enemy_fleet = Fleet(
            id="enemy_fleet",
            roster=strategy.roster,
            cell_factory=enemy_cell_factory,
            allow_placing=False,
            classes="enemy",
        )
        self.enemy_fleet.border_title = "Enemy fleet"

        self.board_map: dict[str, Board] = {
            self._player_name: self.player_board,
            self._enemy_name: self.enemy_board,
        }
        self.fleet_map: dict[str, Fleet] = {
            self._player_name: self.player_fleet,
            self._enemy_name: self.enemy_fleet,
        }
        self.players_ready = 0

        if strategy.salvo_mode:
            self.enemy_board.min_targets = len(strategy.roster)

        self.battle_log = BattleLog()
        self.announcement = Announcement(rules=self._format_rules(RULES_TEMPLATE))
        self.summary: models.GameSummary | None = None

        self._strategy.subscribe("fleet_ready", self.on_fleet_ready)
        self._strategy.subscribe("ship_spawned", self.on_ship_spawned)
        self._strategy.subscribe("awaiting_move", self.on_awaiting_move)
        self._strategy.subscribe("salvo", self.on_salvo)
        self._strategy.subscribe("game_ended", self.on_game_ended)
        self._strategy.subscribe("game_cancelled", self.on_game_cancelled)

    def compose(self) -> ComposeResult:
        with Container():
            with Grid(id="content"):
                yield self.player_board
                yield self.announcement
                yield self.enemy_board
                yield self.player_fleet
                yield self.battle_log
                yield self.enemy_fleet

        yield AppFooter()

    @property
    def game_ended(self) -> bool:
        return self._strategy.winner is not None

    def action_try_quit(self) -> None:
        if self.game_ended:
            self.app.exit()
            return

        def callback(should_quit: bool) -> None:
            if should_quit:
                self.cancel_game()
                self.app.exit()

        self.app.push_screen(SessionEndModal(), callback)

    def write_as_game(self, text: str) -> None:
        now = datetime.now().strftime("%H:%M")
        time = f"[cyan]{now}[/]"
        prefix = "[yellow][Game][/]:"
        self.battle_log.write(f"{time} {prefix} {text}")

    def action_show_summary(self) -> None:
        if self.summary is not None:
            self.app.push_screen(
                GameSummaryModal(
                    player=self._player_name,
                    enemy=self._enemy_name,
                    summary=self.summary,
                )
            )

    @on(Board.ShipPlaced)
    def spawn_ship(self, event: Board.ShipPlaced) -> None:
        self.player_board.mode = Board.Mode.DISPLAY
        position = [convert_to_coordinate(c) for c in event.coordinates]
        self._strategy.spawn_ship(ship_id=event.ship.id, position=position)

    def on_fleet_ready(self, player: str) -> None:
        self.write_as_game(f":ship: {player}'s fleet is ready")
        self.players_ready += 1

        if self.players_ready == 2:
            text = PHASE_BATTLE_SALVO if self._strategy.salvo_mode else PHASE_BATTLE
            self.query_one(Announcement).update_phase(text)

    def on_awaiting_move(self, actor: str, subject: str) -> None:
        if (actor_board := self.board_map[actor]) is self.player_board:
            actor_board.under_attack = True

        actor_board.mode = Board.Mode.DISPLAY

        if (subject_board := self.board_map[subject]) != self.player_board:
            subject_board.mode = Board.Mode.TARGET

        self.write_as_game(f":man: {actor}'s turn. Fire at will!")

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
                result = ":water_wave:"
            else:
                assert shot.ship, "Shot was a hit, but no ship"

                if shot.ship.destroyed:
                    status = ":cross_mark:"
                    board.paint_destroyed(map(convert_from_coordinate, shot.ship.cells))
                else:
                    status = ":fire:"
                    board.paint_damage(coor)

                fleet.damage(shot.ship.id)
                result = f"{status} [b]{shot.ship.type.title()}[/]"

            self.write_as_game(f":dart: {salvo.actor.name} ↠ {shot.coordinate}. {result}")

        if self._strategy.salvo_mode:
            self.board_map[salvo.actor.name].min_targets = salvo.ships_left

    def on_game_ended(self, winner: str, summary: models.GameSummary) -> None:
        self.summary = summary

        for board in self.board_map.values():
            board.mode = Board.Mode.DISPLAY

        self.write_as_game(f":party_popper: [b]{winner}[/] has won!")

        text = PHASE_VICTORY if self._player_name == winner else PHASE_DEFEAT
        self.query_one(Announcement).update_phase(text)
        self._strategy.unsubscribe()

    def on_game_cancelled(self, reason: Literal["quit", "disconnect", "error"]) -> None:
        self._strategy.unsubscribe()
        self.app.pop_screen()

        msg = CANCEL_MSG[reason]

        try:
            msg = msg % self._enemy_name
        except TypeError:
            msg = msg

        if reason == "error":
            self.app.notify(msg, title="Game error", severity="error")
        else:
            self.app.notify(msg, title="Game cancelled", severity="warning")

    @on(Board.CellShot)
    def fire(self, event: Board.CellShot) -> None:
        self.enemy_board.mode = Board.Mode.DISPLAY
        self.player_board.under_attack = False
        position = [convert_to_coordinate(c) for c in event.coordinates]
        self._strategy.fire(position=position)

    def action_back(self) -> None:
        if self.game_ended:
            self.app.pop_screen()
            return

        def callback(should_quit: bool) -> None:
            if should_quit:
                self.cancel_game()
                self.app.pop_screen()

        self.app.push_screen(SessionEndModal(), callback)

    def cancel_game(self) -> None:
        self._strategy.cancel()
        self._strategy.unsubscribe()

    @on(Ship.ShowPreview)
    def show_ship_preview(self, event: Ship.ShowPreview) -> None:
        self.player_board.mode = Board.Mode.ARRANGE
        roster_item = self._strategy.roster[event.ship_key]
        self.player_board.show_ship_preview(ship_id=roster_item.id, ship_hp=roster_item.hp)

    def _format_rules(self, template: str) -> str:
        salvo_mode = "Yes" if self._strategy.salvo_mode else "No"
        firing_order = self._strategy.firing_order.replace("_", " ").capitalize()
        return Template(template).substitute(
            salvo_mode=salvo_mode,
            firing_order=firing_order,
            roster=self._strategy.roster.name.capitalize(),
        )
