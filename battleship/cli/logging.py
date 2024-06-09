import loguru
import sentry_sdk
from sentry_offline import make_offline_transport

from battleship import PACKAGE_NAME, data_home, get_client_version


def configure_logger(sink: str, log_size: str = "1 MB", level: str = "DEBUG") -> None:
    loguru.logger.enable(PACKAGE_NAME)
    loguru.logger.remove()
    loguru.logger.add(sink, rotation=log_size, level=level)


def configure_sentry(dsn: str) -> None:
    sentry_sdk.init(
        dsn,
        transport=make_offline_transport(storage_path=data_home / "sentry_events"),
        release=get_client_version(),
    )
