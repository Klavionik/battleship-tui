import enum
import secrets
from typing import Any, TypeAlias, TypeVar

from pydantic import BaseModel as _BaseModel
from pydantic import EmailStr, Field

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

    @classmethod
    def from_dict(cls: type[T], obj: dict[str, Any]) -> T:
        return cls.model_validate(obj)


class SessionCreate(BaseModel):
    name: str
    roster: str
    firing_order: str
    salvo_mode: bool


class Session(SessionCreate):
    id: SessionID


class User(BaseModel):
    nickname: str
    guest: bool | None = None


class RefreshToken(BaseModel):
    refresh_token: str


class IDToken(BaseModel):
    id_token: str
    expires_at: int


class LoginData(BaseModel):
    nickname: str
    id_token: str
    refresh_token: str
    expires_at: int


class LoginCredentials(BaseModel):
    nickname: str = Field(..., min_length=7, max_length=20)
    password: str = Field(..., min_length=9)


class SignupCredentials(LoginCredentials):
    email: EmailStr


def make_session_id() -> SessionID:
    return f"session_{secrets.token_urlsafe(8)}"
