from datetime import datetime, timezone
from pathlib import Path

import loguru
import sentry_sdk
from sentry_offline import make_offline_transport

from battleship import PACKAGE_NAME, data_home, get_client_version


def configure_logger(debug: bool) -> None:
    if debug:
        now = datetime.now(tz=timezone.utc)
        sink = str(Path() / f"client_{now:%Y-%m-%d_%H-%M-%S}.log")
        log_size = "10 MB"
        level = "DEBUG"
    else:
        sink = str(data_home / "client.log")
        log_size = "5 MB"
        level = "INFO"

    loguru.logger.enable(PACKAGE_NAME)
    loguru.logger.remove()
    loguru.logger.add(sink, rotation=log_size, level=level)


def configure_sentry(dsn: str) -> None:
    sentry_sdk.init(
        dsn,
        transport=make_offline_transport(storage_path=data_home / "sentry_events"),
        release=get_client_version(),
    )
