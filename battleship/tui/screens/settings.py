from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Markdown, OptionList

from battleship.tui import resources, screens
from battleship.tui.widgets import AppFooter


class Settings(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with resources.get_resource("settings_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield Label("Player name")
                yield Input(value="Player")

                yield Label("Your fleet color")
                yield Input(value="FFFFFF")

                yield Label("Enemy fleet color")
                yield Input(value="AAAAAA")

                yield Label("Language")
                yield OptionList("English")

                with Horizontal():
                    yield Button("Reset to defaults", variant="error", id="reset")
                    yield Button("Save", variant="primary", id="save")

        yield AppFooter()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Button.Pressed, "#save")
    def save_settings(self) -> None:
        # TODO: Settings saving.
        self.notify("Settings saved.", title="Success", timeout=5)

    @on(Button.Pressed, "#reset")
    def reset_settings(self) -> None:
        # TODO: Settings reset.
        self.notify("Settings reset.", severity="warning", title="Success", timeout=5)
