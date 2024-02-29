import dataclasses
from functools import cached_property
from itertools import chain
from typing import Callable, Iterable, Iterator, NamedTuple, TypeAlias
from uuid import uuid4

RosterName: TypeAlias = str
ShipId: TypeAlias = str
ShipType: TypeAlias = str
ShipHitpoints: TypeAlias = int
ShipConfig: TypeAlias = tuple[ShipType, ShipHitpoints]
RosterDefinition: TypeAlias = Callable[[], Iterable[ShipConfig]]
RosterRegistry: TypeAlias = dict[RosterName, "Roster"]


class RosterItem(NamedTuple):
    id: ShipId
    type: ShipType
    hp: ShipHitpoints


@dataclasses.dataclass(frozen=True)
class Roster:
    name: RosterName
    items: list[RosterItem]

    def __add__(self, other: "Roster") -> "Roster":
        if not isinstance(other, Roster):
            raise TypeError("Cannot add a Roster to non-Roster.")

        new_roster_name = f"{self.name}+{other.name}"
        new_roster = Roster(
            name=new_roster_name,
            items=[
                RosterItem(str(i), item.type, item.hp) for i, item in enumerate(chain(self, other))
            ],
        )
        return new_roster

    def __iter__(self) -> Iterator[RosterItem]:
        return iter(self.items)

    def __reversed__(self) -> Iterator[RosterItem]:
        return reversed(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, key: str) -> RosterItem:
        return self._items_by_id[key]

    @cached_property
    def _items_by_id(self) -> dict[ShipId, RosterItem]:
        return {item.id: item for item in self.items}


_rosters: RosterRegistry = {}


def register(func: RosterDefinition) -> None:
    roster_name = func.__name__
    _rosters[roster_name] = Roster(
        name=roster_name,
        items=[RosterItem(str(i), type_, hp) for i, (type_, hp) in enumerate(func())],
    )


def get_rosters() -> RosterRegistry:
    return _rosters


def get_roster(name: RosterName) -> Roster:
    return _rosters[name]


def make_item_id() -> str:
    return uuid4().hex[:8]


@register
def classic() -> Iterable[ShipConfig]:
    return (
        ("carrier", 5),
        ("battleship", 4),
        ("cruiser", 3),
        ("submarine", 3),
        ("destroyer", 2),
    )


@register
def russian() -> Iterable[ShipConfig]:
    return (
        ("battleship", 4),
        ("cruiser", 3),
        ("cruiser", 3),
        ("destroyer", 2),
        ("destroyer", 2),
        ("destroyer", 2),
        ("frigate", 1),
        ("frigate", 1),
        ("frigate", 1),
        ("frigate", 1),
    )
