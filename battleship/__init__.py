import os
from functools import cache
from importlib import metadata
from pathlib import Path

from loguru import logger
from xdg_base_dirs import xdg_cache_home, xdg_config_home, xdg_data_home

PACKAGE_NAME = Path().parent.resolve().name


@cache
def get_client_version() -> str:
    return os.getenv("BATTLESHIP_CLIENT_VERSION", metadata.version("battleship-tui"))


APP_LABEL = "battleship"
data_home = xdg_data_home() / APP_LABEL
cache_home = xdg_cache_home() / APP_LABEL
config_home = xdg_config_home() / APP_LABEL

logger.disable(PACKAGE_NAME)

try:
    __version__ = get_client_version()
except metadata.PackageNotFoundError:
    # Probably running on server, this is only a client version.
    __version__ = "0.0.0"
