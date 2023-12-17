from typing import Any

import inject
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Markdown, Select

from battleship.tui import resources, screens
from battleship.tui.settings import Settings as SettingsModel
from battleship.tui.settings import SettingsProvider
from battleship.tui.widgets import AppFooter


class Settings(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    @inject.param("provider", SettingsProvider)
    def __init__(self, *args: Any, provider: SettingsProvider, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.provider = provider
        self.current = provider.load()

        with resources.get_resource("settings_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
                yield Label("Player name")
                yield Input(value=self.current.player_name, id="player_name")

                yield Label("Your fleet color")
                yield Input(value=self.current.fleet_color, id="fleet_color")

                yield Label("Enemy fleet color")
                yield Input(value=self.current.enemy_fleet_color, id="enemy_fleet_color")

                yield Label("Language")
                yield Select.from_values(
                    self.current.language_options,
                    allow_blank=False,
                    value=self.current.language,
                    id="language",
                )

                with Horizontal():
                    yield Button("Reset to defaults", variant="error", id="reset")
                    yield Button("Save", variant="primary", id="save")

        yield AppFooter()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Button.Pressed, "#save")
    def save_settings(self) -> None:
        settings = SettingsModel(
            player_name=self.player_name.value,
            fleet_color=self.fleet_color.value,
            enemy_fleet_color=self.enemy_fleet_color.value,
            language=self.language.value,
        )
        self.provider.save(settings)
        self.notify("Settings saved.", title="Success", timeout=3)

    @on(Button.Pressed, "#reset")
    def reset_settings(self) -> None:
        defaults = self.provider.save_defaults()
        self.player_name.value = defaults.player_name
        self.fleet_color.value = defaults.fleet_color
        self.enemy_fleet_color.value = defaults.enemy_fleet_color
        self.language.value = defaults.language
        self.notify("Settings reset.", severity="warning", title="Success", timeout=3)

    @property
    def player_name(self) -> Input:
        return self.query_one("#player_name", Input)

    @property
    def fleet_color(self) -> Input:
        return self.query_one("#fleet_color", Input)

    @property
    def enemy_fleet_color(self) -> Input:
        return self.query_one("#enemy_fleet_color", Input)

    @property
    def language(self) -> Select[str]:
        return self.query_one("#language", Select)
