import enum
import secrets
from typing import Any, TypeAlias, TypeVar

from pydantic import BaseModel as _BaseModel

SessionID: TypeAlias = str
T = TypeVar("T", bound="BaseModel")


class Action(enum.StrEnum):
    ADD = enum.auto()
    REMOVE = enum.auto()


class BaseModel(_BaseModel):
    def to_json(self) -> str:
        return self.model_dump_json()

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_raw(cls: type[T], data: str | bytes) -> T:
        return cls.model_validate_json(data)


class SessionCreate(BaseModel):
    name: str
    roster: str
    firing_order: str
    salvo_mode: bool


class Session(SessionCreate):
    id: SessionID


class User(BaseModel):
    display_name: str
    id_token: str


def make_session_id() -> SessionID:
    return f"session_{secrets.token_urlsafe(8)}"
