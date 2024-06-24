from typing import Any

import inject
from loguru import logger
from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.events import Mount, Unmount
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

from battleship.client import Client, ClientError, ConnectionEvent, SessionSubscription
from battleship.shared.models import Session, SessionID
from battleship.tui.format import format_session
from battleship.tui.widgets import AppFooter


class SessionItem(ListItem):
    LABEL_TEMPLATE = (
        "$name | Roster: $roster | Firing order: $firing_order | Salvo mode: $salvo_mode"
    )

    def __init__(self, *args: Any, session: Session, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.id = self.get_id(session.id)
        self.log(session)
        self.session = session

    def compose(self) -> ComposeResult:
        yield Label(format_session(self.LABEL_TEMPLATE, self.session))

    @staticmethod
    def get_id(session_id: str) -> str:
        return "session" + session_id


class JoinGame(Screen[None]):
    class JoinMultiplayerSession(Message):
        def __init__(self, session_id: str):
            super().__init__()
            self.session_id = session_id

    BINDINGS = [("escape", "back", "Back")]

    @inject.param("client", Client)
    def __init__(self, *args: Any, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = client
        self._session_list = ListView()
        self._subscription: SessionSubscription | None = None

    def compose(self) -> ComposeResult:
        with Container(classes="container"):
            yield Static("Select a game", id="title")
            yield self._session_list

        yield AppFooter()

    def action_back(self) -> None:
        self.app.pop_screen()

    @on(Mount)
    async def subscribe(self) -> None:
        await self.subscribe_to_updates()
        await self.fetch_sessions()
        self._client.add_listener(ConnectionEvent.CONNECTION_LOST, self.handle_connection_lost)

    @on(Unmount)
    async def unsubscribe(self) -> None:
        await self.unsubscribe_from_updates()
        self._subscription = None
        self._client.remove_listener(ConnectionEvent.CONNECTION_LOST, self.handle_connection_lost)

    def handle_connection_lost(self) -> None:
        async def handle_connection_established() -> None:
            logger.debug("Connection restored, resubscribe to session updates.")
            await self._session_list.query(SessionItem).remove()
            await self.subscribe_to_updates()
            await self.fetch_sessions()

            self._client.remove_listener(
                ConnectionEvent.CONNECTION_IMPOSSIBLE, handle_connection_impossible
            )

        async def handle_connection_impossible() -> None:
            logger.debug("Resubscription to session updates is impossible.")
            self._client.remove_listener(
                ConnectionEvent.CONNECTION_ESTABLISHED, handle_connection_established
            )

        logger.debug("Connection lost, setup handlers in case it is restored (or lost forever).")
        self._client.add_listener(
            ConnectionEvent.CONNECTION_ESTABLISHED, handle_connection_established, once=True
        )
        self._client.add_listener(
            ConnectionEvent.CONNECTION_IMPOSSIBLE, handle_connection_impossible, once=True
        )

    async def fetch_sessions(self) -> None:
        try:
            sessions = await self._client.fetch_sessions()
        except ClientError as exc:
            logger.warning("Cannot fetch sessions. {exc}", exc=exc)
        else:
            for session in sessions:
                await self.add_session(session)

    async def subscribe_to_updates(self) -> None:
        try:
            self._subscription = await self._client.sessions_subscribe()
            self._subscription.on_add(self.add_session)
            self._subscription.on_remove(self.remove_session)
            self._subscription.on_start(self.remove_session)
        except ClientError as exc:
            logger.warning("Cannot subscribe to session updates. {exc}", exc=exc)

    async def unsubscribe_from_updates(self) -> None:
        try:
            await self._client.sessions_unsubscribe()
        except ClientError as exc:
            logger.warning("Cannot unsubscribe from sessions. {exc}", exc=exc)

    @on(ListView.Selected)
    async def join_from_event(self, event: ListView.Selected) -> None:
        item: SessionItem = event.item  # type: ignore
        session = item.session

        self.post_message(self.JoinMultiplayerSession(session.id))

    async def add_session(self, session: Session) -> None:
        item_id = SessionItem.get_id(session.id)

        try:
            # Remove possible duplicate.
            item = self._session_list.query_one(f"#{item_id}")
            await item.remove()
        except NoMatches:
            pass

        await self._session_list.append(SessionItem(session=session))

    async def remove_session(self, session_id: SessionID) -> None:
        item_id = SessionItem.get_id(session_id)

        try:
            item = self._session_list.query_one(f"#{item_id}", ListItem)
            await item.remove()
        except NoMatches:
            pass
