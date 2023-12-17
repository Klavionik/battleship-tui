from abc import ABC, abstractmethod
from pathlib import Path

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


class SettingsProvider(ABC):
    @abstractmethod
    def save(self, settings: Settings) -> None:
        pass

    @abstractmethod
    def load(self) -> Settings:
        pass

    def save_defaults(self) -> Settings:
        defaults = Settings()
        self.save(defaults)
        return defaults


class FilesystemSettingsProvider(SettingsProvider):
    permission = 0o600  # Read-write for user.

    def __init__(self, filename: str = ".settings.json", config_dir: str | None = None):
        config = Path(config_dir) if config_dir else config_home
        self.config = config / filename
        self._ensure_config_dir()

    def save(self, settings: Settings) -> None:
        with self.config.open(mode="w") as cache:
            cache.write(settings.to_json())

        self.config.chmod(self.permission)

    def load(self) -> Settings:
        if not self.config.exists():
            return self.save_defaults()

        with self.config.open() as config:
            try:
                settings = Settings.from_raw(config.read())
            except Exception:  # noqa
                return self.save_defaults()

        return settings

    def _ensure_config_dir(self) -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)


filesystem_settings_provider = FilesystemSettingsProvider()
