from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Markdown, RadioButton, RadioSet

from battleship.engine import domain, roster, session
from battleship.tui import resources, screens


class Singleplayer(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.roster = roster.get_roster("classic")
        self.firing_order = domain.FiringOrder.ALTERNATELY
        self.salvo_mode = False

        with resources.get_resource("singleplayer_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with VerticalScroll():
                yield Markdown(self.help, classes="screen-help")

            with Container(classes="screen-content"):
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
        def session_factory() -> session.SingleplayerSession:
            return session.SingleplayerSession(
                "Player", self.roster, self.firing_order, self.salvo_mode
            )

        self.app.switch_screen(screens.Game(session_factory=session_factory))
