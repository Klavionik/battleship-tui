from typing import Any

import inject
from loguru import logger
from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.events import Mount, Unmount
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Static

from battleship.client import Client, ClientError, SessionSubscription
from battleship.engine.roster import Roster, RosterItem
from battleship.shared.events import ClientEvent, ServerEvent
from battleship.shared.models import Session, SessionID
from battleship.tui import screens, strategies
from battleship.tui.format import format_session


class SessionItem(ListItem):
    LABEL_TEMPLATE = (
        "$name | Roster: $roster | Firing order: $firing_order | Salvo mode: $salvo_mode"
    )

    def __init__(self, *args: Any, session: Session, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.log(session)
        self.session = session

    def compose(self) -> ComposeResult:
        yield Label(format_session(self.LABEL_TEMPLATE, self.session))


class JoinGame(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    @inject.param("client", Client)
    def __init__(self, *args: Any, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = client
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
        await self.subscribe_to_updates()
        await self.fetch_sessions()
        self._client.add_listener(ClientEvent.CONNECTION_LOST, self.resubscribe)

    @on(Unmount)
    async def unsubscribe(self) -> None:
        await self.unsubscribe_from_updates()

    async def resubscribe(self) -> None:
        logger.warning("Resubscribe")
        await self._client.await_connection()
        await self._session_list.query(SessionItem).remove()
        await self.subscribe_to_updates()
        await self.fetch_sessions()
        logger.warning("Resubscribe success")

    async def fetch_sessions(self) -> None:
        sessions = await self._client.fetch_sessions()

        for session in sessions:
            await self.add_session(session)

    async def subscribe_to_updates(self) -> None:
        self._subscription = await self._client.sessions_subscribe()
        self._subscription.on_add(self.add_session)
        self._subscription.on_remove(self.remove_session)
        self._subscription.on_start(self.remove_session)

    async def unsubscribe_from_updates(self) -> None:
        try:
            await self._client.sessions_unsubscribe()
        except ClientError:
            pass

        self._subscription = None
        self._client.remove_listener(ClientEvent.CONNECTION_LOST, self.resubscribe)

    @on(ListView.Selected)
    async def join(self, event: ListView.Selected) -> None:
        item: SessionItem = event.item  # type: ignore
        session = item.session

        def on_start_game(payload: dict[str, Any]) -> None:
            self._client.remove_listener(ServerEvent.START_GAME, on_start_game)

            enemy_nickname = payload["enemy"]
            data = payload["roster"]
            roster = Roster(name=data["name"], items=[RosterItem(*item) for item in data["items"]])

            strategy = strategies.MultiplayerStrategy(
                self._client.nickname,
                enemy_nickname,
                roster,
                session.firing_order,
                session.salvo_mode,
                self._client,
            )

            self.app.push_screen(screens.Game(strategy=strategy))

        self._client.add_listener(ServerEvent.START_GAME, on_start_game)

        await self._client.join_game(session.id)

    async def add_session(self, session: Session) -> None:
        try:
            # Remove possible duplicate.
            item = self._session_list.query_one(f"#{session.id}")
            await item.remove()
        except NoMatches:
            pass

        await self._session_list.append(SessionItem(id=session.id, session=session))

    async def remove_session(self, session_id: SessionID) -> None:
        try:
            item = self._session_list.query_one(f"#{session_id}", ListItem)
            await item.remove()
        except NoMatches:
            pass
