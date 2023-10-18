from datetime import datetime
from typing import Any, Callable, Iterable

from textual import on
from textual.app import DEFAULT_COLORS, ComposeResult
from textual.containers import Grid
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import Footer, Placeholder

from battleship.engine import domain, session
from battleship.tui import screens
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
        self, *args: Any, session_factory: Callable[[], session.SingleplayerSession], **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self._session_factory = session_factory
        self._session = session_factory()

        dark_theme = DEFAULT_COLORS.get("dark")
        assert dark_theme
        colors = dark_theme.generate()

        player_cell_factory = CellFactory(ship_bg=colors["success-darken-1"])
        enemy_cell_factory = CellFactory(ship_bg=colors["accent-darken-1"])

        self.player_board = Board(
            player_name=self._session.player_name,
            size=domain.DEFAULT_BOARD_SIZE,
            cell_factory=player_cell_factory,
            classes="player",
        )
        self.enemy_board = Board(
            player_name=self._session.enemy_name,
            size=domain.DEFAULT_BOARD_SIZE,
            cell_factory=enemy_cell_factory,
            classes="enemy",
        )

        self.player_fleet = Fleet(
            roster=self._session.roster,
            cell_factory=player_cell_factory,
            classes="player",
        )
        self.player_fleet.border_title = "Your fleet"
        self.enemy_fleet = Fleet(
            roster=self._session.roster,
            cell_factory=enemy_cell_factory,
            allow_placing=False,
            classes="enemy",
        )
        self.enemy_fleet.border_title = "Enemy fleet"

        self.board_map = {
            self._session.player_name: self.player_board,
            self._session.enemy_name: self.enemy_board,
        }
        self.fleet_map = {
            self._session.player_name: self.player_fleet,
            self._session.enemy_name: self.enemy_fleet,
        }

        if self._session.salvo_mode:
            self.enemy_board.min_targets = len(self._session.roster)

        self.battle_log = BattleLog()

        self._session.subscribe("fleet_ready", self.on_fleet_ready)
        self._session.subscribe("ship_spawned", self.on_ship_spawned)
        self._session.subscribe("awaiting_move", self.on_awaiting_move)
        self._session.subscribe("salvo", self.on_salvo)
        self._session.subscribe("game_ended", self.on_game_ended)

    def compose(self) -> ComposeResult:
        with Grid(id="content"):
            yield self.player_board
            yield Placeholder()
            yield self.enemy_board
            yield self.player_fleet
            yield self.battle_log
            yield self.enemy_fleet

        yield Footer()

    def on_mount(self) -> None:
        self._session.start()

    def write_as_game(self, text: str) -> None:
        now = datetime.now().strftime("%H:%M")
        time = f"[cyan]{now}[/]"
        prefix = "[yellow][Game][/]:"
        self.battle_log.write(f"{time} {prefix} {text}")

    @on(Board.ShipPlaced)
    def spawn_ship(self, event: Board.ShipPlaced) -> None:
        self.player_board.mode = Board.Mode.DISPLAY
        position = [convert_to_coordinate(c) for c in event.coordinates]
        self._session.notify("spawn_ship", ship_id=event.ship.id, position=position)

    def on_fleet_ready(self, player: domain.Player) -> None:
        self.write_as_game(f"{player.name}'s fleet is ready")

    def on_awaiting_move(self, actor: domain.Player, subject: domain.Player) -> None:
        self.board_map[actor.name].mode = Board.Mode.DISPLAY
        self.board_map[subject.name].mode = Board.Mode.TARGET
        self.write_as_game(f"{actor.name}'s turn. Fire at will!")

    def on_ship_spawned(self, ship_id: str, position: Iterable[str]) -> None:
        self.player_board.paint_ship([convert_from_coordinate(p) for p in position])
        self.player_fleet.place(ship_id)

    def on_salvo(self, salvo: domain.Salvo) -> None:
        board = self.board_map[salvo.subject.name]
        fleet = self.fleet_map[salvo.subject.name]

        for shot in salvo:
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

        if self._session.salvo_mode:
            self.board_map[salvo.actor.name].min_targets = salvo.ships_left

    def on_game_ended(self, winner: domain.Player) -> None:
        for board in self.board_map.values():
            board.mode = Board.Mode.DISPLAY

        self.write_as_game(f"{winner.name} has won!")

    @on(Board.CellShot)
    def fire(self, event: Board.CellShot) -> None:
        self.enemy_board.mode = Board.Mode.DISPLAY
        position = [convert_to_coordinate(c) for c in event.coordinates]
        self._session.notify("fire", position=position)

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Ship.ShowPreview)
    def show_ship_preview(self, event: Ship.ShowPreview) -> None:
        self.player_board.mode = Board.Mode.ARRANGE
        roster_item = self._session.roster[event.ship_key]
        self.player_board.show_ship_preview(ship_id=roster_item.id, ship_hp=roster_item.hp)
