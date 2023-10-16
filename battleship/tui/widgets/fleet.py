from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import Label, Static

from battleship.engine.roster import Roster


class PlaceShipLink(Static):
    class RequestShipPreview(Message):
        def __init__(self, ship_index: int) -> None:
            super().__init__()
            self.ship_index = ship_index

    def __init__(self, *args: Any, ship_type: str, ship_index: int, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._ship_index = ship_index
        self.update(f"[@click=preview({ship_index})]Place {ship_type}[/]\n")

    def action_preview(self) -> None:
        self.post_message(self.RequestShipPreview(self._ship_index))


class Fleet(Widget):
    placed_ships: var[list[int]] = var(list)

    class RequestShipPreview(Message):
        def __init__(self, ship_index: int) -> None:
            super().__init__()
            self.ship_index = ship_index

    def __init__(self, *args: Any, roster: Roster, placeable: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._roster = roster
        self._placeable = placeable

    def compose(self) -> ComposeResult:
        yield Label("[b]Fleet status[/]")

        for index, ship in enumerate(self._roster):
            if index in self.placed_ships or not self._placeable:
                yield Static(Text(" " * 2 * ship.hp + "\n", style="on green"))
            else:
                yield PlaceShipLink(ship_type=ship.type, ship_index=index)
