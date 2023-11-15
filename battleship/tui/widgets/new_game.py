from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.events import Mount
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, RadioButton, RadioSet

from battleship.engine import domain


class NewGame(Widget):
    class PlayPressed(Message):
        def __init__(
            self,
            name: str,
            roster: str,
            firing_order: domain.FiringOrder,
            salvo_mode: bool,
        ) -> None:
            super().__init__()
            self.name = name
            self.roster = roster
            self.firing_order = firing_order
            self.salvo_mode = salvo_mode

    def __init__(self, *args: Any, with_name: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._with_name = with_name
        self.game_name = ""
        self.roster = "classic"
        self.firing_order = domain.FiringOrder.ALTERNATELY
        self.salvo_mode = False

    def compose(self) -> ComposeResult:
        if self._with_name:
            yield Input(placeholder="Game name")

        with RadioSet(id="roster", classes="options-panel") as rs:
            rs.border_title = "Roster"
            yield RadioButton("Classic", name="classic", value=True)
            yield RadioButton("Russian", name="russian")

        with RadioSet(id="firing_order", classes="options-panel") as rs:
            rs.border_title = "Firing order"
            yield RadioButton("Alternately", name="alternately", value=True)
            yield RadioButton("Until miss", name="until_miss")

        yield Checkbox("Salvo mode", name="salvo_mode", id="salvo_mode")
        yield Button("Play", variant="success")

    @on(Mount)
    def focus_name(self) -> None:
        if self._with_name:
            self.query_one(Input).focus()

    @on(Input.Submitted)
    def play(self) -> None:
        self.post_play_pressed()

    @on(Input.Changed)
    def update_name(self, event: Input.Changed) -> None:
        self.game_name = event.value

    @on(RadioSet.Changed, "#roster")
    def update_roster(self, event: RadioSet.Changed) -> None:
        self.roster = event.pressed.name  # type: ignore[assignment]

    @on(RadioSet.Changed, "#firing_order")
    def update_firing_order(self, event: RadioSet.Changed) -> None:
        firing_order = next(fo for fo in domain.FiringOrder if fo == event.pressed.name)
        self.firing_order = firing_order

    @on(Checkbox.Changed, "#salvo_mode")
    def update_salvo_mode(self, event: Checkbox.Changed) -> None:
        self.salvo_mode = event.value

    @on(Button.Pressed)
    def emit_play_pressed(self) -> None:
        with self.prevent(Button.Pressed):
            self.post_play_pressed()

    def post_play_pressed(self) -> None:
        self.post_message(
            self.PlayPressed(
                self.game_name,
                self.roster,
                self.firing_order,
                self.salvo_mode,
            )
        )
