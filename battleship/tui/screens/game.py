from datetime import datetime
from typing import Any, Callable, Iterable

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import Footer, RichLog

from battleship.engine import domain, session
from battleship.tui import screens
from battleship.tui.widgets.board import Board, ShipToPlace


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
        self.player_board = Board(size=domain.DEFAULT_BOARD_SIZE, classes="player")
        self.enemy_board = Board(size=domain.DEFAULT_BOARD_SIZE, classes="enemy")
        self.board_map = {
            self._session.player.name: self.player_board,
            self._session.bot.name: self.enemy_board,
        }

        if self._session.salvo_mode:
            self.enemy_board.min_targets = len(self._session.roster)

        self.chat = RichLog(wrap=True, markup=True)

        self._session.subscribe("fleet_ready", self.on_fleet_ready)
        self._session.subscribe("ship_spawned", self.on_ship_spawned)
        self._session.subscribe("request_ship_position", self.on_request_ship_position)
        self._session.subscribe("awaiting_move", self.on_awaiting_move)
        self._session.subscribe("salvo", self.on_salvo)
        self._session.subscribe("game_ended", self.on_game_ended)

    def compose(self) -> ComposeResult:
        with Horizontal(id="boards"):
            yield self.player_board
            yield self.chat
            yield self.enemy_board

        yield Footer()

    def on_mount(self) -> None:
        self._session.start()

    def write_as_game(self, text: str) -> None:
        now = datetime.now().strftime("%H:%M")
        time = f"[cyan]{now}[/]"
        prefix = "[yellow][Game][/]:"
        self.chat.write(f"{time} {prefix} {text}")

    def on_request_ship_position(self, hp: int, ship_type: str) -> None:
        self.player_board.mode = Board.Mode.ARRANGE
        self.write_as_game(f"Place your :ship: [b]{ship_type.title()}[/]")
        self.player_board.set_ship_to_place(ShipToPlace(type=ship_type, length=hp))

    @on(Board.ShipPlaced)
    def spawn_ship(self, event: Board.ShipPlaced) -> None:
        self.player_board.mode = Board.Mode.DISPLAY
        position = [convert_to_coordinate(c) for c in event.coordinates]
        self._session.notify("spawn_ship", position=position, ship_type=event.ship.type)

    def on_fleet_ready(self, player: domain.Player) -> None:
        self.write_as_game(f"{player.name}'s fleet is ready")

    def on_awaiting_move(self, actor: domain.Player, subject: domain.Player) -> None:
        self.board_map[actor.name].mode = Board.Mode.DISPLAY
        self.board_map[subject.name].mode = Board.Mode.TARGET
        self.write_as_game(f"{actor.name}'s turn. Fire at will!")

    def on_ship_spawned(self, position: Iterable[str]) -> None:
        self.player_board.paint_ship([convert_from_coordinate(p) for p in position])

    def on_salvo(self, salvo: domain.Salvo) -> None:
        board = self.board_map[salvo.subject.name]

        for shot in salvo:
            coor = convert_from_coordinate(shot.coordinate)

            if shot.miss:
                board.paint_miss(coor)
                result = "Miss"
            else:
                board.paint_damage(coor)
                hit_or_destroyed = "sunk" if shot.ship.destroyed else "hit"  # type: ignore
                result = f"{shot.ship.type.title()} {hit_or_destroyed}"  # type: ignore

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
