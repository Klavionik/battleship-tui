from typing import Callable

import loguru
from xdg_base_dirs import xdg_data_home

DEFAULT_CLIENT_SINK = xdg_data_home() / "battleship" / "client.log"


def filter_by(keyword: str) -> Callable[["loguru.Record"], bool]:
    def filter_(record: "loguru.Record") -> bool:
        return keyword in record["extra"]

    return filter_


loguru.logger.remove()
loguru.logger.add(
    str(DEFAULT_CLIENT_SINK), rotation="1 MB", filter=filter_by("client"), level="DEBUG"
)

client_logger = loguru.logger.bind(client=True)
