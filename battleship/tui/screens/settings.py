from typing import Any

import inject
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.validation import Length, ValidationResult, Validator
from textual.widgets import Button, Input, Label, Markdown, Select

from battleship.tui import resources, screens
from battleship.tui.settings import Settings as SettingsModel
from battleship.tui.settings import SettingsProvider, hex_color, validate_color
from battleship.tui.widgets import AppFooter


class HexColor(Validator):
    def validate(self, value: str) -> ValidationResult:
        try:
            validate_color(value)
            return self.success()
        except ValueError as exc:
            return self.failure(str(exc))


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
        with Container(classes="container"):
            with VerticalScroll():
                yield Markdown(
                    self.help,
                )

            with Container():
                yield Label("Player name")
                yield Input(
                    value=self.current.player_name,
                    id="player_name",
                    validators=[Length(minimum=1, maximum=19)],
                )

                yield Label("Your fleet color")
                yield Input(
                    value=self.current.fleet_color,
                    id="fleet_color",
                    restrict=hex_color.pattern,
                    validators=[HexColor()],
                )

                yield Label("Enemy fleet color")
                yield Input(
                    value=self.current.enemy_fleet_color,
                    id="enemy_fleet_color",
                    restrict=hex_color.pattern,
                    validators=[HexColor()],
                )

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
        if not (
            self.player_name.is_valid
            and self.fleet_color.is_valid
            and self.enemy_fleet_color.is_valid
        ):
            self.notify(
                "Cannot save: some fields have invalid values.", severity="warning", timeout=5
            )
            return

        settings = SettingsModel(
            player_name=self.player_name.value,
            fleet_color=self.fleet_color.value,
            enemy_fleet_color=self.enemy_fleet_color.value,
            language=self.language.value,
        )

        saved = self.provider.save(settings)

        if saved:
            self.notify("Settings saved.", timeout=3)
        else:
            self.notify("No changes to save.", severity="warning", timeout=5)

    @on(Button.Pressed, "#reset")
    def reset_settings(self) -> None:
        self.provider.reset()
        defaults = self.provider.load()
        self.player_name.value = defaults.player_name
        self.fleet_color.value = defaults.fleet_color
        self.enemy_fleet_color.value = defaults.enemy_fleet_color
        self.language.value = defaults.language
        self.notify("Settings reset.", timeout=3)

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
