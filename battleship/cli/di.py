import inject

from battleship import tui
from battleship.client import Client


def configure_injection(settings: tui.Config) -> None:
    def configure_(binder: inject.Binder) -> None:
        client = Client(str(settings.server_url), settings.credentials_provider)
        binder.bind(Client, client)

    inject.configure(configure_)
