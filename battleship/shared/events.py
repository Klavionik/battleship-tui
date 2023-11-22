from enum import auto
from typing import Any, TypeAlias, TypedDict

from battleship.shared.compat import StrEnum
from battleship.shared.models import BaseModel


class ClientEvent(StrEnum):
    SESSIONS_SUBSCRIBE = auto()
    SESSIONS_UNSUBSCRIBE = auto()
    SPAWN_SHIP = auto()
    FIRE = auto()
    CANCEL_GAME = auto()
    CONNECTION_LOST = auto()
    CONNECTION_ESTABLISHED = auto()
    CONNECTION_IMPOSSIBLE = auto()


class ServerEvent(StrEnum):
    SESSIONS_UPDATE = auto()
    START_GAME = auto()
    SHIP_SPAWNED = auto()
    FLEET_READY = auto()
    AWAITING_MOVE = auto()
    SALVO = auto()
    GAME_ENDED = auto()
    GAME_CANCELLED = auto()
    PLAYERS_UPDATE = auto()


Event: TypeAlias = ServerEvent | ClientEvent
EventPayload: TypeAlias = dict[str, Any]


class EventMessageDataBase(TypedDict):
    kind: Event


class EventMessageData(EventMessageDataBase, total=False):
    payload: EventPayload


class EventMessage(BaseModel):
    kind: Event
    payload: EventPayload = {}
