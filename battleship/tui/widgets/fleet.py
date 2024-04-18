from typing import Any, Callable

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.events import Mount
from textual.message import Message
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import Static

from battleship.engine.rosters import Roster
from battleship.tui.widgets.board import CellFactory


class Ship(Static):
    previewing: var[bool] = var(False, init=False)

    class ShowPreview(Message):
        def __init__(self, ship_key: str) -> None:
            super().__init__()
            self.ship_key = ship_key

    def __init__(
        self,
        *args: Any,
        key: str,
        ship_type: str,
        hp: int,
        factory: Callable[[int, int, bool], Text],
        allow_placing: bool,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._ship_type = ship_type
        self._hp = hp
        self._damage = 0
        self._key = key
        self._allow_placing = allow_placing
        self._placed = False
        self._factory = factory

    @property
    def type_display(self) -> str:
        return self._ship_type.title()

    @property
    def destroyed(self) -> bool:
        return self.hp == 0

    @property
    def hp(self) -> int:
        return self._hp - self._damage

    @on(Mount)
    def on_mount(self) -> None:
        if self._allow_placing:
            self.render_place_link()
        else:
            self.render_ship()

    def place(self) -> None:
        self.render_ship()
        self.tooltip = self.type_display
        self._placed = True

    def damage(self) -> None:
        if self._damage + 1 <= self._hp:
            self._damage += 1

        self.render_ship()

    def render_ship(self) -> None:
        self.update(self._factory(self.hp, self._damage, self.destroyed))

    def render_place_link(self, previewing: bool = False) -> None:
        end = " <-\n" if previewing else "\n"
        self.update(f"[@click=preview()]Place {self.type_display}[/]{end}")

    def watch_previewing(self, _: bool, new: bool) -> None:
        if not self._placed:
            self.render_place_link(previewing=new)

    def action_preview(self) -> None:
        self.post_message(self.ShowPreview(self._key))


class Fleet(Widget):
    previewing_id: var[str] = var("")

    def __init__(
        self,
        *args: Any,
        roster: Roster,
        cell_factory: CellFactory,
        allow_placing: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        def ship_factory(hp: int, damage: int, destroyed: bool) -> Text:
            if destroyed:
                parts = [cell_factory.destroyed().render() for _ in range(damage)]
                return Text.assemble(*parts, "\n")

            hp_parts = [cell_factory.ship().render() for _ in range(hp)]
            damage_parts = [cell_factory.damaged().render() for _ in range(damage)]
            return Text.assemble(*(hp_parts + damage_parts), "\n")

        self._roster = roster
        self._allow_placing = allow_placing
        self._previewing_id = ""
        self._ships: dict[str, Ship] = {
            ship.id: Ship(
                id=f"ship_{ship.id}",
                key=ship.id,
                ship_type=ship.type,
                hp=ship.hp,
                allow_placing=allow_placing,
                factory=ship_factory,
            )
            for ship in roster
        }

    def watch_previewing_id(self, old: str, new: str) -> None:
        if old:
            self._ships[old].previewing = False

        if new:
            self._ships[new].previewing = True

    def compose(self) -> ComposeResult:
        yield from self._ships.values()

    @on(Ship.ShowPreview)
    def handle_show_preview(self, event: Ship.ShowPreview) -> None:
        self.previewing_id = event.ship_key  # noqa

    def place(self, ship_id: str) -> None:
        ship = self._ships[ship_id]
        ship.place()
        self.previewing_id = ""  # noqa

    def damage(self, ship_id: str) -> None:
        ship = self._ships[ship_id]
        ship.damage()
