from pydantic import HttpUrl, ImportString
from pydantic_settings import BaseSettings

from battleship.client import CredentialsProvider
from battleship.tui.settings import SettingsProvider


class Config(BaseSettings):
    server_url: HttpUrl
    credentials_provider: ImportString[CredentialsProvider]
    game_settings_provider: ImportString[SettingsProvider]
