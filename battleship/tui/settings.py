import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from battleship import config_home
from battleship.shared.models import BaseModel


class Settings(BaseModel):
    player_name: str = "Player"
    fleet_color: str = "#36aa5e"
    enemy_fleet_color: str = "#0065be"
    language: str = "English"

    @property
    def language_options(self) -> list[str]:
        return ["English"]

    @classmethod
    def get_changed(cls, settings: "Settings") -> dict[str, Any]:
        defaults = cls().to_dict()
        settings_dump = settings.to_dict()
        return {k: v for k, v in settings_dump.items() if v != defaults[k]}


class SettingsProvider(ABC):
    @abstractmethod
    def save(self, settings: Settings) -> None:
        pass

    @abstractmethod
    def load(self) -> Settings:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass


class FilesystemSettingsProvider(SettingsProvider):
    permission = 0o600  # Read-write for user.

    def __init__(self, filename: str = ".settings.json", config_dir: str | None = None):
        config = Path(config_dir) if config_dir else config_home
        self.config = config / filename
        self._ensure_config_dir()

    def save(self, settings: Settings) -> None:
        changed = Settings.get_changed(settings)

        if len(changed):
            with self.config.open(mode="w") as file:
                json.dump(changed, file)

            self.config.chmod(self.permission)

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
