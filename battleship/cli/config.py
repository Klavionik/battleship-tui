from functools import cache

from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    SERVER_URL: HttpUrl = HttpUrl("http://localhost:8000")


@cache
def get_config() -> Config:
    return Config()
