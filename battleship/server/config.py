from pydantic import RedisDsn
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    TRACE: bool
    AUTH0_DOMAIN: str
    AUTH0_CLIENT_ID: str
    AUTH0_CLIENT_SECRET: str
    AUTH0_REALM: str
    AUTH0_ROLES: dict[str, str]
    REDIS_URL: RedisDsn
    SERVER_VERSION: str
    SENTRY_DSN: str
    METRICS_SCRAPER_SECRET: str

    @property
    def auth0_audience(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/api/v2/"

    @property
    def auth0_issuer(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/"

    @property
    def auth0_jwks_url(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/.well-known/jwks.json"


def get_config() -> Config:
    return Config()
