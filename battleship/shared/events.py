from enum import StrEnum
from typing import Any, NotRequired, TypeAlias, TypedDict

from battleship.shared.models import BaseModel


class ClientEvent(StrEnum):
    LOGIN = "login"
    LOGOUT = "logout"
    SESSIONS_SUBSCRIBE = "sessions_subscribe"
    SESSIONS_UNSUBSCRIBE = "sessions_unsubscribe"


class ServerEvent(StrEnum):
    LOGIN = "login"
    SESSIONS_UPDATE = "sessions_update"


Event: TypeAlias = ServerEvent | ClientEvent
EventPayload: TypeAlias = dict[str, Any]


class EventMessageData(TypedDict):
    kind: Event
    payload: NotRequired[EventPayload]


class EventMessage(BaseModel):
    kind: Event
    payload: EventPayload = {}
