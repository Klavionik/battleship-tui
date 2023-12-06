from functools import cache
from importlib import metadata

from xdg_base_dirs import xdg_cache_home, xdg_data_home


@cache
def get_client_version() -> str:
    return metadata.version("battleship-tui")


APP_LABEL = "battleship"
data_home = xdg_data_home() / APP_LABEL
cache_home = xdg_cache_home() / APP_LABEL

try:
    __version__ = get_client_version()
except metadata.PackageNotFoundError:
    # Probably running on server, this is only a client version.
    __version__ = "0.0.0"
