import loguru

from battleship import PACKAGE_NAME


def configure_logger(sink: str, log_size: str = "1 MB", level: str = "DEBUG") -> None:
    loguru.logger.enable(PACKAGE_NAME)
    loguru.logger.remove()
    loguru.logger.add(sink, rotation=log_size, level=level)
