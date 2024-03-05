import uuid
from enum import auto, unique
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import UUID4, Field

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
    GAME_ENDED = auto()
    GAME_CANCELLED = auto()


@unique
class Notification(StrEnum):
    SESSIONS_UPDATE = auto()
    PLAYERS_UPDATE = auto()


class GameEvent(BaseModel):
    message_type: Literal["game_event"] = "game_event"
    type: ServerGameEvent | ClientGameEvent
    payload: dict[str, Any] = {}


class EntityEvent(BaseModel):
    message_type: Literal["entity_event"] = "entity_event"
    entity: Literal["session", "client", "statistics"]
    entity_id: str
    action: str
    payload: dict[str, Any] = {}


class NotificationEvent(BaseModel):
    message_type: Literal["notification_event"] = "notification_event"
    notification: Notification
    payload: dict[str, Any]


AnyEvent: TypeAlias = NotificationEvent | GameEvent | EntityEvent
T = TypeVar("T", bound=AnyEvent)


class Message(BaseModel, Generic[T]):
    correlation_id: UUID4 = Field(default_factory=uuid.uuid4)
    event: AnyEvent = Field(..., discriminator="message_type")


AnyMessage: TypeAlias = Message[NotificationEvent] | Message[GameEvent] | Message[EntityEvent]
