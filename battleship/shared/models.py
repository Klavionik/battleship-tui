import random
import string
from enum import auto
from typing import Any, TypeAlias, TypeVar

from pydantic import BaseModel as _BaseModel
from pydantic import EmailStr, Field, computed_field

from battleship.engine import domain, rosters
from battleship.shared.compat import StrEnum

SessionID: TypeAlias = str
T = TypeVar("T", bound="BaseModel")


class Action(StrEnum):
    ADD = auto()
    REMOVE = auto()
    START = auto()


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
    duration: int = 0
    shots: dict[str, int] = {}
    hits: dict[str, int] = {}
    ships_left: int = 0
    hp_left: int = 0
    winner: str | None = None

    def add_shot(self, user_id: str, hit: bool = True) -> None:
        self.shots[user_id] = self.get_shots(user_id) + 1

        if hit:
            self.hits[user_id] = self.get_hits(user_id) + 1

    def accuracy(self, player: str) -> float:
        shots = self.get_shots(player)

        if not shots:
            return 0

        hits = self.get_hits(player)
        return round(hits / shots, 1)

    def get_shots(self, player: str) -> int:
        return self.shots.get(player, 0)

    def get_hits(self, player: str) -> int:
        return self.hits.get(player, 0)

    def update_shots(self, salvo: domain.Salvo) -> None:
        for shot in salvo:
            self.add_shot(salvo.actor.name, hit=shot.hit)

    def finalize(self, winner: domain.Player, start: float, end: float) -> None:
        self.winner = winner.name
        self.duration = int(end - start)
        self.ships_left = winner.ships_alive

        for ship in winner.ships:
            if not ship.destroyed:
                self.hp_left += ship.hp


class PlayerStatistics(BaseModel):
    user_id: str
    games_played: int = 0
    games_won: int = 0
    shots: int = 0
    hits: int = 0
    total_duration: int = 0
    quickest_win_shots: int = 0
    quickest_win_duration: int = 0

    @computed_field  # type: ignore[misc]
    @property
    def accuracy(self) -> float:
        if not self.shots:
            return 0
        return round(self.hits / self.shots, 1)

    @computed_field  # type: ignore[misc]
    @property
    def avg_duration(self) -> int:
        if not self.games_played:
            return 0
        return round(self.total_duration / self.games_played)

    @computed_field  # type: ignore[misc]
    @property
    def win_ratio(self) -> float:
        if not self.games_played:
            return 0
        return round(self.games_won / self.games_played, 1)

    def update_from_summary(self, summary: GameSummary) -> None:
        self.games_played += 1

        if summary.winner == self.user_id:
            self.games_won += 1

            if summary.duration < self.quickest_win_duration:
                self.quickest_win_duration = summary.duration

            if summary.get_hits(self.user_id) < self.quickest_win_shots:
                self.quickest_win_shots = summary.duration

        self.shots += summary.get_shots(self.user_id)
        self.hits += summary.get_hits(self.user_id)
        self.total_duration += summary.duration


class Client(BaseModel):
    id: str
    nickname: str
    guest: bool
    version: str


class PlayerCount(BaseModel):
    total: int
    ingame: int


class RosterItem(BaseModel):
    id: str
    type: str
    hp: int


class Roster(BaseModel):
    name: str
    items: list[RosterItem]

    @classmethod
    def from_domain(cls, obj: rosters.Roster) -> "Roster":
        items = [RosterItem(id=item.id, type=item.type, hp=item.hp) for item in obj.items]
        return cls(name=obj.name, items=items)


def make_session_id(length: int = 6) -> SessionID:
    alphabet = string.ascii_uppercase + string.digits
    id_ = "".join(random.choices(alphabet, k=length))
    return id_
