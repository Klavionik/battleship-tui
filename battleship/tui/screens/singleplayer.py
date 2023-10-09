from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Markdown, RadioButton, RadioSet

from battleship.engine import domain, roster
from battleship.tui import screens

SINGLEPLAYER_TEXT = """
# Help
In Singleplayer mode you play against the AI. You can configure options before the game starts.

**Roster**
Choose ship types that will be present on the battlefield.

1. *Classic* - Carrier (5 HP), Battleship (4 HP), Cruiser (3 HP), Submarine (3 HP), Destroyer (2 HP)
2. *Russian* - Battleship (4 HP), Cruiser (3 HP) x2, Destroyer (2 HP) x3, Frigate (1 HP) x4

**Firing order**
Choose, whether players make turns one at a time, or until the first miss.

**Salvo mode**
Toggles salvo mode. In salvo mode, players make as many shots during the turn as they have ships
left.
"""


class Singleplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.roster = roster.get_roster("classic")
        self.firing_order = domain.FiringOrder.ALTERNATELY
        self.salvo_mode = False

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            with VerticalScroll():
                yield Markdown(SINGLEPLAYER_TEXT, id="text")

            with Container(id="options"):
                with RadioSet(id="roster") as rs:
                    rs.border_title = "Roster"
                    yield RadioButton("Classic", name="classic", value=True)
                    yield RadioButton("Russian", name="russian")

                with RadioSet(id="firing_order") as rs:
                    rs.border_title = "Firing order"
                    yield RadioButton("Alternately", name="alternately", value=True)
                    yield RadioButton("Until miss", name="until_miss")
                yield Checkbox("Salvo mode", name="salvo_mode", id="salvo_mode")

                yield Button("Play", variant="success")

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(RadioSet.Changed, "#roster")
    def update_roster(self, event: RadioSet.Changed) -> None:
        self.roster = roster.get_roster(event.pressed.name)  # type: ignore[arg-type]

    @on(RadioSet.Changed, "#firing_order")
    def update_firing_order(self, event: RadioSet.Changed) -> None:
        firing_order = next(fo for fo in domain.FiringOrder if fo == event.pressed.name)
        self.firing_order = firing_order

    @on(Checkbox.Changed, "#salvo_mode")
    def update_salvo_mode(self, event: Checkbox.Changed) -> None:
        self.salvo_mode = event.value

    @on(Button.Pressed)
    def start_game(self) -> None:
        def game_factory() -> domain.Game:
            return domain.Game(
                player_a=domain.Player("Player"),
                player_b=domain.Player("Computer"),
                roster=self.roster,
                firing_order=self.firing_order,
                salvo_mode=self.salvo_mode,
            )

        # TODO: Switch to game screen.
