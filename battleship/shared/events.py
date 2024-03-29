from enum import auto, unique
from typing import Any, Generic, Literal, TypeAlias, TypeVar, cast

from pydantic import Field

from battleship.shared.compat import StrEnum
from battleship.shared.models import BaseModel


@unique
class ClientGameEvent(StrEnum):
    SPAWN_SHIP = auto()
    FIRE = auto()
    CANCEL_GAME = auto()


@unique
class ServerGameEvent(StrEnum):
    START_GAME = auto()
    SHIP_SPAWNED = auto()
    FLEET_READY = auto()
    AWAITING_MOVE = auto()
    SALVO = auto()
    CANCEL_GAME = auto()
    GAME_ENDED = auto()
    GAME_CANCELLED = auto()


@unique
class Subscription(StrEnum):
    PLAYERS_UPDATE = auto()
    SESSIONS_UPDATE = auto()


class GameEvent(BaseModel):
    message_type: Literal["game_event"] = "game_event"
    type: ServerGameEvent | ClientGameEvent
    session_id: str | None = None
    payload: dict[str, Any] = {}


Entity = Literal["session", "client", "statistics"]


class EntityEvent(BaseModel):
    message_type: Literal["entity_event"] = "entity_event"
    entity: Entity
    entity_id: str
    action: str
    payload: dict[str, Any] = {}


class NotificationEvent(BaseModel):
    message_type: Literal["notification_event"] = "notification_event"
    subscription: Subscription
    payload: dict[str, Any]


class ClientDisconnectedEvent(BaseModel):
    message_type: Literal["client_disconnected"] = "client_disconnected"
    client_id: str


AnyEvent: TypeAlias = NotificationEvent | GameEvent | EntityEvent | ClientDisconnectedEvent
T = TypeVar("T", bound=AnyEvent)


class Message(BaseModel, Generic[T]):
    event: AnyEvent = Field(..., discriminator="message_type")

    def unwrap(self) -> T:
        return cast(T, self.event)


AnyMessage: TypeAlias = (
    Message[NotificationEvent]
    | Message[GameEvent]
    | Message[EntityEvent]
    | Message[ClientDisconnectedEvent]
)
