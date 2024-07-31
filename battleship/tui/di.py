from rodi import Container

from battleship.client import Client
from battleship.client.credentials import CredentialsProvider
from battleship.tui.config import Config
from battleship.tui.settings import SettingsProvider

container = Container()


def configure(config: Config) -> None:
    container.add_instance(config.credentials_provider(), CredentialsProvider)
    container.add_instance(config.game_settings_provider(), SettingsProvider)
    container.add_instance(
        Client(str(config.server_url), container.resolve(CredentialsProvider)), Client
    )
