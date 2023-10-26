from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

from xdg_base_dirs import xdg_cache_home

from battleship.shared.models import BaseModel

DEFAULT_LEEWAY_SECONDS = 30


class Credentials(BaseModel):
    nickname: str
    id_token: str
    refresh_token: str = ""
    expires_at: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def is_expired(self, leeway: int = DEFAULT_LEEWAY_SECONDS) -> bool:
        delta = timedelta(seconds=leeway)
        now = datetime.now()
        return now > (self.expires_at - delta)


class CredentialsProvider(ABC):
    @abstractmethod
    def save(self, credentials: Credentials) -> None:
        pass

    @abstractmethod
    def load(self) -> Credentials | None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass


class FilesystemCredentialsProvider(CredentialsProvider):
    root = "battleship"
    permission = 0o600  # Read-write for user.

    def __init__(self, filename: str = ".credentials", cache_dir: str | None = None):
        cache = Path(cache_dir) if cache_dir else xdg_cache_home()
        self.cache = cache / self.root / filename

    def save(self, credentials: Credentials) -> None:
        with self.cache.open(mode="w") as cache:
            cache.write(credentials.to_json())

        self.cache.chmod(self.permission)

    def load(self) -> Credentials | None:
        if not self.cache.exists():
            return None

        with self.cache.open() as cache:
            credentials = Credentials.from_raw(cache.read())

        if credentials.is_expired():
            return None

    def clear(self) -> None:
        self.cache.unlink(missing_ok=True)
