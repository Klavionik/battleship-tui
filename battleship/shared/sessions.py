import dataclasses
import enum
import secrets
from typing import TypeAlias

SessionId: TypeAlias = str


class Action(enum.StrEnum):
    ADD = enum.auto()
    REMOVE = enum.auto()


@dataclasses.dataclass
class Session:
    id: SessionId
    name: str
    roster: str
    firing_order: str
    salvo_mode: bool


def make_session_id() -> SessionId:
    return f"session_{secrets.token_urlsafe(8)}"
