import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Annotated, Any

from pydantic import AfterValidator, Field

from battleship import config_home
from battleship.shared.models import BaseModel
from battleship.tui.i18n import Language

hex_color = re.compile(r"^#([0-9a-f]{0,6})$")


def validate_color(value: str) -> str:
    color = hex_color.match(value)

    if color is None:
        raise ValueError(f"Value {value} is not a valid hex color.")
    return value


HexColor = Annotated[str, AfterValidator(validate_color)]


class Settings(BaseModel):
    player_name: str = Field("Player", max_length=19)
    fleet_color: HexColor = "#36aa5e"
    enemy_fleet_color: HexColor = "#0065be"
    language: Language = Language.ENGLISH

    @property
    def language_options(self) -> list[str]:
        return list(Language)

    def diff(self, settings: "Settings") -> dict[str, Any]:
        self_dump = self.to_dict()
        settings_dump = settings.to_dict()
        return {k: v for k, v in settings_dump.items() if v != self_dump[k]}


class SettingsProvider(ABC):
    @abstractmethod
    def save(self, settings: Settings) -> bool:
        pass

    @abstractmethod
    def load(self) -> Settings:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass


class InMemorySettingsProvider(SettingsProvider):
    def __init__(self) -> None:
        self._settings = Settings()

    def save(self, settings: Settings) -> bool:
        self._settings = settings
        return True

    def load(self) -> Settings:
        return self._settings

    def reset(self) -> None:
        self._settings = Settings()


class FilesystemSettingsProvider(SettingsProvider):
    permission = 0o600  # Read-write for user.

    def __init__(self, filename: str = ".settings.json", config_dir: str | None = None):
        config = Path(config_dir) if config_dir else config_home
        self.config = config / filename
        self._ensure_config_dir()

    def save(self, settings: Settings) -> bool:
        current = self.load()
        changes = current.diff(settings)

        if not changes:
            return False

        with self.config.open(mode="w") as file:
            json.dump(changes, file)

        self.config.chmod(self.permission)
        return True

    def load(self) -> Settings:
        if not self.config.exists():
            return Settings()

        try:
            with self.config.open() as config:
                user_settings = json.load(config)
        except Exception:  # noqa
            return Settings()

        return Settings(**user_settings)

    def reset(self) -> None:
        self.config.unlink(missing_ok=True)

    def _ensure_config_dir(self) -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)


filesystem_settings_provider = FilesystemSettingsProvider()
in_memory_settings_provider = InMemorySettingsProvider()
