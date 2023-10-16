from typing import Any

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.events import Mount
from textual.message import Message
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import Label, Static

from battleship.engine.roster import Roster


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
        is_player: bool,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._ship_type = ship_type
        self._hp = hp
        self._key = key
        self._is_player = is_player

    @on(Mount)
    def on_mount(self) -> None:
        if self._is_player:
            self.render_place_link()
        else:
            self.render_ship()

    def place(self) -> None:
        self.render_ship()

    def render_ship(self) -> None:
        style = "on green" if self._is_player else "on red"
        self.update(Text(" " * 2 * self._hp + "\n", style=style))

    def render_place_link(self) -> None:
        self.update(f"[@click=preview('{self._key}')]Place {self._ship_type.title()}[/]\n")

    def action_preview(self) -> None:
        self.post_message(self.ShowPreview(self._key))


class Fleet(Widget):
    placed_ships: var[list[int]] = var(list)

    def __init__(self, *args: Any, roster: Roster, is_player: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._roster = roster
        self._is_player = is_player
        self._ships = {
            ship.id: Ship(key=ship.id, ship_type=ship.type, hp=ship.hp, is_player=self._is_player)
            for ship in roster
        }

    def compose(self) -> ComposeResult:
        yield Label("[b]Fleet status[/]")
        yield from self._ships.values()

    def place(self, ship_id: str) -> None:
        ship = self._ships[ship_id]
        ship.place()
