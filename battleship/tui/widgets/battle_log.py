from typing import Any

from textual.widgets import RichLog


class BattleLog(RichLog):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("wrap", True)
        kwargs.setdefault("markup", True)
        super().__init__(*args, **kwargs)
        self.border_title = "Battle log"
