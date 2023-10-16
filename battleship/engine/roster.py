import dataclasses
from typing import Callable, Iterable, Iterator, NamedTuple, TypeAlias

RosterName: TypeAlias = str
ShipType: TypeAlias = str
ShipHitpoints: TypeAlias = int
ShipConfig: TypeAlias = tuple[ShipType, ShipHitpoints]
RosterDefinition: TypeAlias = Callable[[], Iterable[ShipConfig]]
RosterRegistry: TypeAlias = dict[RosterName, "Roster"]


class RosterItem(NamedTuple):
    type: ShipType
    hp: ShipHitpoints


@dataclasses.dataclass(frozen=True, slots=True)
class Roster:
    name: RosterName
    items: list[RosterItem]

    def __add__(self, other: "Roster") -> "Roster":
        if not isinstance(other, Roster):
            raise TypeError("Cannot add a Roster to non-Roster.")

        new_roster_name = f"{self.name}+{other.name}"
        new_roster = Roster(name=new_roster_name, items=self.items.copy() + self.items.copy())
        return new_roster

    def __iter__(self) -> Iterator[RosterItem]:
        return iter(self.items)

    def __reversed__(self) -> Iterator[RosterItem]:
        return reversed(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, item: int) -> RosterItem:
        return self.items[item]


_rosters: RosterRegistry = {}


def register(func: RosterDefinition) -> None:
    roster_name = func.__name__
    _rosters[roster_name] = Roster(
        name=roster_name, items=[RosterItem(type_, hp) for type_, hp in func()]
    )


def get_rosters() -> RosterRegistry:
    return _rosters


def get_roster(name: RosterName) -> Roster:
    return _rosters[name]


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
