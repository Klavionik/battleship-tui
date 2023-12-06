from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

from battleship import cache_home
from battleship.shared.models import BaseModel

DEFAULT_LEEWAY_SECONDS = 30


class Credentials(BaseModel):
    user_id: str
    nickname: str
    id_token: str
    refresh_token: str = ""
    expires_at: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def is_expired(self, leeway: int = DEFAULT_LEEWAY_SECONDS) -> bool:
        delta = timedelta(seconds=leeway)
        now = datetime.now(tz=timezone.utc)
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


class DummyCredentialsProvider(CredentialsProvider):
    def save(self, credentials: Credentials) -> None:
        pass

    def load(self) -> Credentials | None:
        pass

    def clear(self) -> None:
        pass


class FilesystemCredentialsProvider(CredentialsProvider):
    permission = 0o600  # Read-write for user.

    def __init__(self, filename: str = ".credentials.json", cache_dir: str | None = None):
        cache = Path(cache_dir) if cache_dir else cache_home
        self.cache = cache / filename
        self._ensure_cache_dir()

    def save(self, credentials: Credentials) -> None:
        with self.cache.open(mode="w") as cache:
            cache.write(credentials.to_json())

        self.cache.chmod(self.permission)

    def load(self) -> Credentials | None:
        if not self.cache.exists():
            return None

        with self.cache.open() as cache:
            try:
                credentials = Credentials.from_raw(cache.read())
            except Exception:  # noqa
                self.clear()
                return None

        return credentials

    def clear(self) -> None:
        self.cache.unlink(missing_ok=True)

    def _ensure_cache_dir(self) -> None:
        self.cache.parent.mkdir(parents=True, exist_ok=True)


dummy_credentials_provider = DummyCredentialsProvider()
filesystem_credentials_provider = FilesystemCredentialsProvider()
