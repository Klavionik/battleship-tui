from functools import cache

from rich.console import Console as _Console
from rich.theme import Theme


class Console(_Console):
    def error(self, text: str) -> None:
        self.print(f"[error]{text}[/]")

    def success(self, text: str) -> None:
        self.print(f"[success]{text}[/]")

    def warning(self, text: str) -> None:
        self.print(f"[warning]{text}[/]")


DEFAULT_THEME = Theme({"error": "red", "success": "green", "accent": "cyan", "warning": "yellow"})


def build_console(theme: Theme) -> Console:
    return Console(theme=theme)


@cache
def get_console() -> Console:
    return build_console(DEFAULT_THEME)
