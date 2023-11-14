import enum
import secrets
from typing import Any, TypeAlias, TypeVar

from pydantic import BaseModel as _BaseModel
from pydantic import EmailStr, Field

from battleship.engine import domain

SessionID: TypeAlias = str
T = TypeVar("T", bound="BaseModel")


class Action(enum.StrEnum):
    ADD = enum.auto()
    REMOVE = enum.auto()
    START = enum.auto()


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
    host_id: str
    started: bool = False
    guest_id: str = ""


class RefreshToken(BaseModel):
    refresh_token: str


class IDToken(BaseModel):
    id_token: str
    expires_at: int


class LoginData(BaseModel):
    user_id: str
    nickname: str
    id_token: str
    refresh_token: str
    expires_at: int


class LoginCredentials(BaseModel):
    nickname: str = Field(..., min_length=7, max_length=20)
    password: str = Field(..., min_length=9)


class SignupCredentials(LoginCredentials):
    email: EmailStr


class Player(BaseModel):
    name: str
    ships_alive: int


class Ship(BaseModel):
    id: str
    type: str
    destroyed: bool
    cells: list[str]


class Shot(BaseModel):
    coordinate: str
    hit: bool
    ship: Ship | None

    @property
    def miss(self) -> bool:
        return not self.hit


class Salvo(BaseModel):
    actor: Player
    subject: Player
    shots: list[Shot] = []

    @property
    def miss(self) -> bool:
        return all(shot.miss for shot in self.shots)

    @property
    def ships_left(self) -> int:
        return self.subject.ships_alive

    def __len__(self) -> int:
        return len(self.shots)


def salvo_to_model(salvo: domain.Salvo) -> Salvo:
    def serialize_ship(ship: domain.Ship | None) -> Ship | None:
        if ship is None:
            return None

        return Ship(id=ship.id, type=ship.type, destroyed=ship.destroyed, cells=ship.cells)

    def serialize_player(player: domain.Player) -> Player:
        return Player(name=player.name, ships_alive=player.ships_alive)

    def serialize_shot(shot: domain.Shot) -> Shot:
        return Shot(coordinate=shot.coordinate, hit=shot.hit, ship=serialize_ship(shot.ship))

    return Salvo(
        actor=serialize_player(salvo.actor),
        subject=serialize_player(salvo.subject),
        shots=[serialize_shot(shot) for shot in salvo],
    )


class GameSummary(BaseModel):
    duration: int = -1
    shots: dict[str, int] = {}
    ships_left: int = -1
    hp_left: int = -1
    winner: str | None = None

    def add_shot(self, user_id: str) -> None:
        self.shots[user_id] = self.shots.get(user_id, 0) + 1


def make_session_id() -> SessionID:
    return f"session_{secrets.token_urlsafe(8)}"
