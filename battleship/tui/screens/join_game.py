import dataclasses
from string import Template
from typing import Any

import pyee
from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Mount, Unmount
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Static

from battleship.client.realtime import get_client


@dataclasses.dataclass
class Session:
    name: str
    roster: str
    firing_order: str
    salvo_mode: bool


class SessionItem(Label):
    TEMPLATE = "$name | Roster: $roster | Firing order: $firing_order | Salvo mode: $salvo_mode"

    def __init__(self, *args: Any, session: Session, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._session = session
        self.update(self.format_session())

    def format_session(self) -> str:
        salvo_mode = "Yes" if self._session.salvo_mode else "No"
        firing_order = self._session.firing_order.replace("_", " ").capitalize()
        return Template(self.TEMPLATE).substitute(
            name=self._session.name,
            salvo_mode=salvo_mode,
            firing_order=firing_order,
            roster=self._session.roster.capitalize(),
        )


class JoinGame(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._subscription: pyee.AsyncIOEventEmitter | None = None
        self._session_list = ListView()

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            yield Static("Select a game", id="title")
            yield self._session_list

        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()

    @on(Mount)
    async def subscribe(self) -> None:
        client = get_client()

        async def update_list(update: dict[str, tuple]) -> None:  # type: ignore[type-arg]
            self.log.debug(f"Received update {update}")
            updates = []

            try:
                for session_id, session in update["items"]:
                    node_id = f"session_{session_id}"
                    updates.append(ListItem(SessionItem(session=Session(**session)), id=node_id))

                await self._session_list.clear()
                await self._session_list.extend(updates)
            except Exception as exc:
                self.log.error(exc)

        self._subscription = await client.sessions_subscribe()
        self._subscription.add_listener("update", update_list)

    @on(Unmount)
    async def unsubscribe(self) -> None:
        client = get_client()
        await client.sessions_unsubscribe()
