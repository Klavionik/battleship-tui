from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Markdown, RadioButton, RadioSet

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

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            with VerticalScroll():
                yield Markdown(SINGLEPLAYER_TEXT, id="text")

            with Container(id="options"):
                with RadioSet(id="roster") as rs:
                    rs.border_title = "Roster"
                    yield RadioButton("Classic", value=True)
                    yield RadioButton("Russian")

                with RadioSet(id="firing_order") as rs:
                    rs.border_title = "Firing order"
                    yield RadioButton("Alternately", value=True)
                    yield RadioButton("Until miss")
                yield Checkbox("[b]Salvo mode[/]", id="salvo_mode")

                yield Button("Play", variant="success")

        yield Footer()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())
