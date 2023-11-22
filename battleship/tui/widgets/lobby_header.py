from typing import Any

from rich.console import RenderableType
from textual.reactive import reactive
from textual.widget import Widget


class LobbyHeader(Widget):
    players_online: reactive[int] = reactive(1)
    players_ingame: reactive[int] = reactive(0)

    def __init__(self, *args: Any, nickname: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._nickname = nickname

    def render(self) -> RenderableType:
        players = "players" if self.players_online > 1 else "player"
        return (
            f"👤{self._nickname} |"
            f" {self.players_online} {players} online ({self.players_ingame} in-game)"
        )
