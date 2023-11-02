from enum import StrEnum, auto
from typing import Any, NotRequired, TypeAlias, TypedDict

from battleship.shared.models import BaseModel


class ClientEvent(StrEnum):
    LOGIN = auto()
    LOGOUT = auto()
    SESSIONS_SUBSCRIBE = auto()
    SESSIONS_UNSUBSCRIBE = auto()
    SPAWN_SHIP = auto()
    FIRE = auto()


class ServerEvent(StrEnum):
    LOGIN = auto()
    SESSIONS_UPDATE = auto()
    START_GAME = auto()
    SHIP_SPAWNED = auto()
    FLEET_READY = auto()
    AWAITING_MOVE = auto()
    SALVO = auto()
    GAME_ENDED = auto()


Event: TypeAlias = ServerEvent | ClientEvent
EventPayload: TypeAlias = dict[str, Any]


class EventMessageData(TypedDict):
    kind: Event
    payload: NotRequired[EventPayload]


class EventMessage(BaseModel):
    kind: Event
    payload: EventPayload = {}
