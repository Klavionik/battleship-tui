import dataclasses
import json
from enum import StrEnum
from typing import Any, NotRequired, Self, TypeAlias, TypedDict


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


@dataclasses.dataclass
class EventMessage:
    kind: Event
    payload: EventPayload = dataclasses.field(default_factory=dict)

    def as_json(self) -> str:
        return json.dumps(dataclasses.asdict(self))

    @classmethod
    def from_raw(cls, data: str | bytes) -> Self:
        return cls(**json.loads(data))
