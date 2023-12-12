from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Label, Rule, Static

RULES_TEMPLATE = """
[b]▪ Roster[/]: $roster
[b]▪ Firing order[/]: $firing_order
[b]▪ Salvo mode[/]: $salvo_mode
"""

PHASE_ARRANGE = """
[b]Current phase[/]: [black on white]ARRANGE FLEET[/]

Select a ship in the left bottom corner of the screen. Use [b]Right Click[/] to rotate the ship and [b]Left Click[/] to place the ship to position.
"""  # noqa: E501

PHASE_BATTLE = """
[b]Current phase[/]: [black on white]BATTLE[/]

On your turn, use [b]Left Click[/] to select a target to attack on the enemy board. The outcome of your shot will be displayed in the battle log.
"""  # noqa: E501

PHASE_BATTLE_SALVO = """
[b]Current phase[/]: [black on white]BATTLE[/]

On your turn, use [b]Left Click[/] to select targets to attack on the enemy board. Use [b]Right Click[/] to reset selected targets. The outcome of your salvo will be displayed in the battle log.
"""  # noqa: E501

PHASE_VICTORY = """
[b]Current phase[/]: [green on white]VICTORY[/]

Congratulations, Admiral! Your excellent commandship led your fleet to a well-deserved victory.

[@click=screen.back()]Back[/]  [@click=screen.show_summary()]Summary[/]
"""

PHASE_DEFEAT = """
[b]Current phase[/]: [red on white]DEFEAT[/]

You may have lost this battle... Still, you haven't lost the war!

[@click=screen.back()]Back[/]  [@click=screen.show_summary()]Summary[/]
"""


class Announcement(Widget):
    def __init__(self, *args: Any, rules: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.border_title = "Announcement"
        self._rules = Label(rules, id="rules")
        self._phase = Static(PHASE_ARRANGE, id="phase")

    def compose(self) -> ComposeResult:
        yield Label("Welcome to the battle, Admiral!", id="welcome")

        with Horizontal():
            yield self._rules
            yield Rule().vertical()
            yield self._phase

    def update_phase(self, text: str) -> None:
        self._phase.update(text)
