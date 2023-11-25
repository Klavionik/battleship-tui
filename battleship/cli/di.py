import inject

from battleship import tui
from battleship.client import Client
from battleship.client.credentials import CredentialsProvider


def configure_injection(settings: tui.Config) -> None:
    def configure_(binder: inject.Binder) -> None:
        binder.bind(CredentialsProvider, settings.credentials_provider)
        binder.bind(Client, Client(str(settings.server_url), settings.credentials_provider))

    inject.configure(configure_)
