from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Mount
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, LoadingIndicator

from battleship.shared import models


class WaitingModal(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Waiting for the second player...")
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
            yield LoadingIndicator()


class GameSummaryModal(ModalScreen[None]):
    def __init__(self, *args: Any, player_name: str, summary: models.GameSummary, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._player_name = player_name
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
        table.add_row(self._format_duration(), label="Duration")
        table.add_row(self._format_shots(), label="Shots")
        table.add_row(str(self._summary.ships_left), label="Ships left")
        table.add_row(str(self._summary.hp_left), label="Ship HP left")
        return table

    def _format_shots(self) -> str:
        shots = self._summary.shots.copy()
        player_shots = shots.pop(self._player_name)
        _, enemy_shots = shots.popitem()
        return f"{player_shots} (you), {enemy_shots} (enemy)"

    def _format_duration(self) -> str:
        minutes = self._summary.duration // 60
        seconds = self._summary.duration % 60

        if minutes > 0:
            return f"{minutes} min {seconds} s"
        return f"{seconds} s"

    @on(Button.Pressed)
    def close(self) -> None:
        self.dismiss()
