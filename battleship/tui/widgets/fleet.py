from typing import Any, Callable

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.events import Mount
from textual.message import Message
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import Label, Static

from battleship.engine.roster import Roster
from battleship.tui.widgets.board import CellFactory


class Ship(Static):
    SHIP_STYLE = {"player": "on green", "enemy": "on red"}

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
        factory: Callable[[int], Text],
        allow_placing: bool,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._ship_type = ship_type
        self._hp = hp
        self._key = key
        self._allow_placing = allow_placing
        self._factory = factory

    @on(Mount)
    def on_mount(self) -> None:
        if self._allow_placing:
            self.render_place_link()
        else:
            self.render_ship()

    def place(self) -> None:
        self.render_ship()

    def render_ship(self) -> None:
        self.update(self._factory(self._hp))

    def render_place_link(self) -> None:
        self.update(f"[@click=preview('{self._key}')]Place {self._ship_type.title()}[/]\n")

    def action_preview(self) -> None:
        self.post_message(self.ShowPreview(self._key))


class Fleet(Widget):
    placed_ships: var[list[int]] = var(list)

    def __init__(
        self,
        *args: Any,
        roster: Roster,
        cell_factory: CellFactory,
        allow_placing: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        def ship_factory(hp: int) -> Text:
            return Text.assemble(*[cell_factory.ship().render() for _ in range(hp)], "\n")

        self._roster = roster
        self._allow_placing = allow_placing
        self._ships = {
            ship.id: Ship(
                key=ship.id,
                ship_type=ship.type,
                hp=ship.hp,
                allow_placing=allow_placing,
                factory=ship_factory,
            )
            for ship in roster
        }

    def compose(self) -> ComposeResult:
        yield Label("[b]Fleet status[/]")
        yield from self._ships.values()

    def place(self, ship_id: str) -> None:
        ship = self._ships[ship_id]
        ship.place()
