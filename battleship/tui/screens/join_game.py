from string import Template
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.events import Mount, Unmount
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Static

from battleship.client import SessionSubscription, get_client
from battleship.shared.models import Session, SessionID


class SessionLabel(Label):
    TEMPLATE = "$name | Roster: $roster | Firing order: $firing_order | Salvo mode: $salvo_mode"

    def __init__(self, *args: Any, session: Session, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.update(self.format_session(session))

    def format_session(self, session: Session) -> str:
        salvo_mode = "Yes" if session.salvo_mode else "No"
        firing_order = session.firing_order.replace("_", " ").capitalize()
        return Template(self.TEMPLATE).substitute(
            name=session.name,
            salvo_mode=salvo_mode,
            firing_order=firing_order,
            roster=session.roster.capitalize(),
        )


class JoinGame(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._session_list = ListView()
        self._subscription: SessionSubscription | None = None

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

        sessions = await client.fetch_sessions()

        for session in sessions:
            await self.add_session(session)

    @on(Unmount)
    async def unsubscribe(self) -> None:
        client = get_client()
        await client.sessions_unsubscribe()
        self._subscription = None

    async def add_session(self, session: Session) -> None:
        try:
            # Remove possible duplicate.
            item = self._session_list.query_one(f"#{session.id}")
            await item.remove()
        except NoMatches:
            pass

        await self._session_list.append(
            ListItem(
                SessionLabel(session=session),
                id=session.id,
            )
        )

    async def remove_session(self, session_id: SessionID) -> None:
        try:
            item = self._session_list.query_one(f"#{session_id}", ListItem)
            await item.remove()
        except NoMatches:
            pass
