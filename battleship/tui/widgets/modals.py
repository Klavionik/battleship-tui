from typing import Any

import copykitten
from rich.console import RenderableType
from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Mount
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, LoadingIndicator

from battleship.shared import models
from battleship.tui.format import format_duration


class GameCode(Label):
    def __init__(self, *args: Any, value: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._value = value

    def render(self) -> RenderableType:
        return f"Game code: [@click=copy()]{self._value}[/]"

    def action_copy(self) -> None:
        copykitten.copy(self._value)
        self.notify("Copied!", timeout=1)


class WaitingModal(ModalScreen[bool]):
    def __init__(self, *args: Any, game_code: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._game_code = game_code

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Waiting for the second player...")
            yield GameCode(value=self._game_code)

            with Container(id="loading"):
                yield LoadingIndicator()

            with Container(id="buttons"):
                yield Button("Abort", variant="error")

    @on(Button.Pressed)
    def abort_waiting(self) -> None:
        self.dismiss(False)


class SessionEndModal(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Are you sure you want to end this session?")

            with Container(id="buttons"):
                yield Button("Yes", id="yes", variant="error")
                yield Button("No", id="no", variant="primary")

    @on(Mount)
    def focus_no(self) -> None:
        self.query_one("#no").focus()

    @on(Button.Pressed, "#yes")
    def end(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def stay(self) -> None:
        self.dismiss(False)


class ConnectionLostModal(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Connection to the server is lost.")
            yield Label("Trying to reconnect...")

            with Container(id="loading"):
                yield LoadingIndicator()


class GameSummaryModal(ModalScreen[None]):
    def __init__(
        self, *args: Any, player: str, enemy: str, summary: models.GameSummary, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self._player = player
        self._enemy = enemy
        self._summary = summary
        self._table = self._make_table()

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("[b]Game summary[/]")
            yield self._table

            with Container(id="buttons"):
                yield Button("Close", variant="error")

    def _make_table(self) -> DataTable[str]:
        table: DataTable[str] = DataTable()
        table.add_columns("")
        table.add_row(format_duration(self._summary.duration), label="Duration")
        table.add_row(self._format_shots(), label="Shots")
        table.add_row(self._format_accuracy(), label="Accuracy")
        table.add_row(str(self._summary.ships_left), label="Ships left")
        table.add_row(str(self._summary.hp_left), label="Ship HP left")
        return table

    def _format_accuracy(self) -> str:
        player_accuracy = self._summary.accuracy(self._player)
        enemy_accuracy = self._summary.accuracy(self._enemy)
        return f"{player_accuracy * 100}% (you), {enemy_accuracy * 100}% (enemy)"

    def _format_shots(self) -> str:
        player_shots = self._summary.get_shots(self._player)
        enemy_shots = self._summary.get_shots(self._enemy)
        return f"{player_shots} (you), {enemy_shots} (enemy)"

    @on(Button.Pressed)
    def close(self) -> None:
        self.dismiss()
