import inject

from battleship import tui
from battleship.client import Client
from battleship.client.credentials import CredentialsProvider
from battleship.tui.settings import SettingsProvider


def configure_injection(config: tui.Config) -> None:
    def configure_(binder: inject.Binder) -> None:
        binder.bind(CredentialsProvider, config.credentials_provider)
        binder.bind(SettingsProvider, config.game_settings_provider)
        binder.bind(Client, Client(str(config.server_url), config.credentials_provider))

    inject.configure(configure_)
