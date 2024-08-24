from typing import Any

from loguru import logger
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import ScreenResume, ScreenSuspend
from textual.screen import Screen
from textual.widgets import DataTable, Markdown

from battleship.shared.models import PlayerStatistics
from battleship.tui import resources
from battleship.tui.format import format_duration
from battleship.tui.widgets import AppFooter


class Statistics(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, data: PlayerStatistics, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._data = data

        with resources.get_resource("statistics_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="container"):
            with VerticalScroll():
                yield Markdown(
                    self.help,
                )

            with Container():
                yield self._make_table()

        yield AppFooter()

    def action_back(self) -> None:
        self.app.pop_screen()

    def _make_table(self) -> DataTable[str]:
        stats = self._data

        table: DataTable[str] = DataTable()
        table.add_columns("")
        table.add_row(str(stats.games_played), label="Games played")
        table.add_row(f"{stats.win_ratio * 100}%", label="Win/loss ratio")
        table.add_row(str(stats.shots), label="Shots")
        table.add_row(f"{stats.accuracy * 100}%", label="Accuracy")
        table.add_row(format_duration(stats.avg_duration), label="Avg game duration")
        table.add_row(format_duration(stats.quickest_win), label="Quickest win")
        return table

    @on(ScreenResume)
    def log_enter(self) -> None:
        logger.info("Enter {screen} screen.", screen=self.__class__.__name__)

    @on(ScreenSuspend)
    def log_leave(self) -> None:
        logger.info("Leave {screen} screen.", screen=self.__class__.__name__)
