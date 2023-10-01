# mypy: ignore-errors
import asyncio
import string
from typing import Callable

from rich.emoji import EMOJI
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import DataTable, Footer, RichLog, Static

from battleship.engine import ai, domain

SHIP = EMOJI["ship"]
WATER = EMOJI["water_wave"]
FIRE = EMOJI["fire"]
CROSS = EMOJI["cross_mark"]

STOP = object()
UPDATE = object()


class Simulator:
    def __init__(
        self,
        game: domain.Game,
        q: asyncio.Queue,
        callback: Callable[[domain.Player], None],
        logger: Callable[[Text], None],
    ):
        self.game = game
        self.queue = q
        self.update_callback = callback
        self.log = logger

    def autoplace(self):
        for player in self.game.players:
            arranger = ai.Autoplacer(player.board, self.game.ship_suite)

            for type_, _ in self.game.ship_suite:
                position = arranger.place(type_)
                self.game.add_ship(player, position, type_)

            self.update_callback(player)

    async def run(self):
        self.autoplace()
        callers = {
            self.game.current_player: ai.TargetCaller(self.game.player_under_attack.board),
            self.game.player_under_attack: ai.TargetCaller(self.game.current_player.board),
        }

        self.game.start()
        self.log(Text("Game started", style="bold yellow"))
        moves_count = 0

        while event := await self.queue.get():
            if event is STOP:
                self.log(Text("Stop simulation", style="bold red"))
                return

            target = callers[self.game.current_player].call_out()
            attempt: domain.FireAttempt  # type: ignore
            [attempt] = self.game.fire(target)
            self.log(
                Text(
                    f"{attempt.actor} strikes {attempt.subject} at {attempt.coordinate}: "
                    f"{f'{attempt.ship.type} hit' if attempt.hit else 'miss'}",
                    style="bold",
                )
            )

            if attempt.ship and attempt.ship.destroyed:
                self.log(Text(f"{attempt.subject}'s {attempt.ship.type} sunk!", style="bold red"))

            moves_count += 1
            self.update_callback(attempt.subject)

        self.log(
            Text(f"Game ended in {moves_count} moves, {self.game.winner} won.", style="bold yellow")
        )


class GameBoard(Widget):
    def __init__(self, *args, player: str, size: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = player
        self.board_size = size

    def on_mount(self):
        self.initialize_grid()

    def initialize_grid(self):
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns(*string.ascii_uppercase[: self.board_size])

        for row in range(1, self.board_size + 1):
            label = Text(str(row), style="#B0FC38 italic")
            cells = []
            for _ in range(self.board_size):
                cells.append(Text(WATER))

            table.add_row(*cells, label=label)

    def compose(self) -> ComposeResult:
        yield Static(f"Player {self.player}")
        yield DataTable()

    def update_grid(self, board: domain.Board):
        table = self.query_one(DataTable)
        table.clear()

        for number, row in enumerate(board.grid, start=1):
            label = Text(str(number), style="#B0FC38 italic")
            cells = []

            for cell in row:
                if cell.ship is not None:
                    if cell.is_shot:
                        cells.append(FIRE)
                    else:
                        cells.append(SHIP)
                else:
                    if cell.is_shot:
                        cells.append(CROSS)
                    else:
                        cells.append(WATER)

            table.add_row(*cells, label=label)


initial_bindings = [
    ("s", "simulate", "Simulate"),
]

step_simulation_bindings = [
    ("r", "reset", "Reset"),
    ("e", "run", "Run"),
    ("w", "move", "Step"),
]

run_simulation_bindings = [
    ("p", "pause", "Pause"),
    ("f", "fast_forward", "Fast forward"),
]


class SimulatorApp(App):
    BINDINGS = list(initial_bindings)
    CSS_PATH = "styles.tcss"

    def __init__(self, *args, game_factory: Callable[[], domain.Game], **kwargs):
        super().__init__(*args, **kwargs)
        self.game: domain.Game = game_factory()
        self.game_factory = game_factory
        self.game_queue = asyncio.Queue()
        self._run_simulator = False
        self._footer = Footer()
        self._fast_forward = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield GameBoard(id="a", classes="box", player=self.game.current_player.name, size=10)
            yield GameBoard(
                id="b", classes="box", player=self.game.player_under_attack.name, size=10
            )
        yield RichLog()
        yield self._footer

    def action_reset(self):
        self.game_queue.put(STOP)
        self.game = self.game_factory()

        for widget in self.query(GameBoard):
            widget.initialize_grid()

        self.update_bindings(initial_bindings)

    def action_pause(self):
        self._run_simulator = False
        self.update_bindings(step_simulation_bindings)

    async def action_move(self):
        if self.game.ended:
            await self.game_queue.put(False)
            return

        await self.game_queue.put(True)

    def action_fast_forward(self):
        self._fast_forward = not self._fast_forward

    def action_run(self):
        self._run_simulator = True

        async def runner():
            while self._run_simulator:
                if self.game.ended:
                    await self.game_queue.put(False)
                    return

                await self.game_queue.put(True)
                await asyncio.sleep(0.05 if self._fast_forward else 1)

        self.run_worker(runner)
        self.update_bindings(run_simulation_bindings)

    def update_bindings(self, new_bindings: list[tuple[str, str, str]]):
        default_bindings = {b.key for b in App.BINDINGS}  # type: ignore

        # Clear current bindings, preserving the default ones.
        for key in list(self._bindings.keys):
            if key not in default_bindings:
                self._bindings.keys.pop(key)

        # Assign new bindings.
        for key, action, description in new_bindings:
            self.bind(key, action, description=description)

        # Notify the footer about binding changes.
        self._footer._bindings_changed(None)

    def action_simulate(self):
        self.update_bindings(step_simulation_bindings)
        log = self.query_one(RichLog)
        log.clear()
        simulator = Simulator(
            game=self.game,
            q=self.game_queue,
            callback=self.refresh_board,
            logger=self.write_log,
        )
        self.run_worker(simulator.run)

    def refresh_board(self, player: domain.Player):
        [widget] = [widget for widget in self.query(GameBoard) if widget.player == player.name]
        widget.update_grid(player.board)

    def write_log(self, text: Text):
        logger = self.query_one(RichLog)
        logger.write(text)


def make_game():
    return domain.Game(
        domain.Player(name="Computer 1"),
        domain.Player(name="Computer 2"),
        domain.CLASSIC_SHIP_SUITE,
    )


if __name__ == "__main__":
    app = SimulatorApp(game_factory=make_game)
    asyncio.run(app.run_async(), debug=True)
