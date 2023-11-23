from functools import cache
from importlib import metadata


@cache
def get_client_version() -> str:
    return metadata.version("battleship-tui")


try:
    __version__ = get_client_version()
except metadata.PackageNotFoundError:
    # Probably running on server, this is only a client version.
    __version__ = "0.0.0"
