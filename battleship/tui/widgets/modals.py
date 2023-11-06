from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Mount
from textual.screen import ModalScreen
from textual.widgets import Button, Label, LoadingIndicator


class WaitingModal(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Waiting for the second player...")
            yield LoadingIndicator()

            with Container(id="buttons"):
                yield Button("Abort", variant="error")

    @on(Button.Pressed)
    def abort_waiting(self) -> None:
        self.dismiss(False)


class SessionEndModal(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Are you sure you want to end this session?")

            with Container(id="buttons"):
                yield Button("Yes", id="yes", variant="error")
                yield Button("No", id="no", variant="primary")

    @on(Mount)
    def focus_no(self) -> None:
        self.query_one("#no").focus()

    @on(Button.Pressed, "#yes")
    def end(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def stay(self) -> None:
        self.dismiss(False)
