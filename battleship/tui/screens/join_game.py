from string import Template
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Mount, Unmount
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Static

from battleship.client.realtime import SessionSubscription, get_client
from battleship.shared.sessions import Session, SessionId


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
        self._subscription: SessionSubscription | None = None
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

        self._subscription = await client.sessions_subscribe()
        self._subscription.on_add(self.add_session)
        self._subscription.on_remove(self.remove_session)

    @on(Unmount)
    async def unsubscribe(self) -> None:
        client = get_client()
        await client.sessions_unsubscribe()
        self._subscription = None

    async def add_session(self, session: Session) -> None:
        await self._session_list.append(
            ListItem(
                SessionItem(session=session),
                id=session.id,
            )
        )

    async def remove_session(self, session_id: SessionId) -> None:
        await self._session_list.query_one(session_id, ListItem).remove()
