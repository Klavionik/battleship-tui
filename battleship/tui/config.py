from pydantic import HttpUrl, ImportString
from pydantic_settings import BaseSettings

from battleship.client import CredentialsProvider


class Config(BaseSettings):
    server_url: HttpUrl
    credentials_provider: ImportString[CredentialsProvider]
