from importlib import metadata

try:
    __version__ = metadata.version("battleship-tui")
except metadata.PackageNotFoundError:
    # Probably running on server, this is only a client version.
    __version__ = "0.0.0"
