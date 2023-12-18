from dataclasses import dataclass
from typing import Any

import inject
import typer
from pydantic import ValidationError
from rich.table import Table

from battleship.cli.console import get_console
from battleship.tui.settings import Settings, SettingsProvider

app = typer.Typer(help="Manage game settings.")


@dataclass
class Setting:
    key: str
    value: str
    default: str
    type: str
    choices: str = "-"


def make_settings_table() -> Table:
    table = Table()

    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Default")
    table.add_column("Type")
    table.add_column("Choices")

    return table


def prepare_settings_data() -> list[Setting]:
    data = []

    settings_provider: SettingsProvider = inject.instance(SettingsProvider)
    settings = settings_provider.load()
    dump = settings.to_dict()
    schema = settings.model_json_schema()
    properties: dict[str, Any] = schema["properties"]
    language = properties.pop("language")

    for key, prop in properties.items():
        setting = Setting(key=key, value=dump[key], default=prop["default"], type=prop["type"])
        data.append(setting)

    # Language is a bit special.
    language_default = language["default"]
    language_definition = schema["$defs"]["Language"]

    try:
        language_choices = language_definition["enum"]
    except KeyError:
        language_choices = [language_definition["const"]]

    data.append(
        Setting(
            key="language",
            value=dump["language"],
            default=language_default,
            type="string",
            choices=", ".join(language_choices),
        )
    )

    return data


@app.command(name="list", help="Display current settings.")
def list_settings() -> None:
    console = get_console()
    table = make_settings_table()
    settings_data = prepare_settings_data()

    for setting in settings_data:
        table.add_row(setting.key, setting.value, setting.default, setting.type, setting.choices)

    console.print(table)


@app.command(
    name="get",
    help="Retrieve current value of a key. Use `settings list` command to discover possible keys.",
)
def get_value(key: str) -> None:
    console = get_console()
    settings_provider: SettingsProvider = inject.instance(SettingsProvider)
    settings = settings_provider.load().to_dict()

    value = settings.get(key)

    if value is None:
        raise typer.Exit(1)

    console.print(value)


@app.command(name="set", help="Set key to a value.")
def set_value(key: str, value: str) -> None:
    console = get_console()
    settings_provider: SettingsProvider = inject.instance(SettingsProvider)
    settings = settings_provider.load()

    try:
        new_settings = Settings(**{**settings.to_dict(), key: value})
    except ValidationError as exc:
        errors = exc.errors()
        msg = errors[0]["msg"]
        console.print(f"[error]{key}[/]: {msg}")
        raise typer.Exit(1)

    saved = settings_provider.save(new_settings)

    if saved:
        console.success(f"Set {key} to {value}.")
    else:
        console.print(f"Nothing to save, {key} already has value of {value}.")
