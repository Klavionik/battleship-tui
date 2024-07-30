from rodi import Container

from battleship.client import Client
from battleship.client.credentials import CredentialsProvider
from battleship.tui.config import Config
from battleship.tui.settings import SettingsProvider

container = Container()


def configure(config: Config) -> None:
    container.add_singleton(CredentialsProvider, config.credentials_provider)
    container.add_singleton(SettingsProvider, config.game_settings_provider)
    container.add_instance(
        Client(str(config.server_url), container.resolve(CredentialsProvider)), Client
    )
