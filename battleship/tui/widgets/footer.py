from rich.console import RenderableType
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Footer

from battleship import get_client_version


class Version(Widget):
    def render(self) -> RenderableType:
        return f"v{get_client_version()}"


class AppFooter(Widget):
    def compose(self) -> ComposeResult:
        footer = Footer()
        footer.upper_case_keys = True
        footer.ctrl_to_caret = False
        yield footer
        yield Version()
