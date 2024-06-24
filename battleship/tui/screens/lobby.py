from typing import Any

import inject
from loguru import logger
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Mount, ScreenResume, ScreenSuspend, Unmount
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Markdown

from battleship.client import Client, ClientError, ConnectionEvent, PlayerSubscription
from battleship.tui import resources, screens
from battleship.tui.widgets import AppFooter, LobbyHeader


class Lobby(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    @inject.param("client", Client)
    def __init__(self, *args: Any, nickname: str, client: Client, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._nickname = nickname
        self._client = client
        self._player_subscription: PlayerSubscription | None = None

        with resources.get_resource("lobby_help.md").open() as fh:
            self.help = fh.read()

    def compose(self) -> ComposeResult:
        with Container(classes="container"):
            with VerticalScroll():
                yield Markdown(
                    self.help,
                )

            with Container():
                yield LobbyHeader(nickname=self._nickname)

                with ListView():
                    yield ListItem(Label("🎯 Create game"), id="create_game")
                    yield ListItem(Label("🔍 Join game"), id="join_game")
                    yield ListItem(Label("📜 Statistics"), id="stats")
                    yield ListItem(Label("👋 Logout"), id="logout")

        yield AppFooter()

    def action_back(self) -> None:
        self.app.switch_screen(screens.MainMenu())

    @on(Mount)
    async def on_mount(self) -> None:
        self.query_one(ListView).focus()

    @on(ScreenSuspend)
    async def unsubscribe(self) -> None:
        await self.unsubscribe_from_player_count()

        self._player_subscription = None
        self._client.remove_listener(ConnectionEvent.CONNECTION_LOST, self.handle_connection_lost)

    @on(ScreenResume)
    async def update_players_count(self) -> None:
        await self._setup_player_count_updates()
        self._client.add_listener(ConnectionEvent.CONNECTION_LOST, self.handle_connection_lost)

    @on(Unmount)
    async def disconnect_ws(self) -> None:
        await self._client.disconnect()

    @on(ListView.Selected, item="#logout")
    async def logout(self) -> None:
        await self._client.disconnect()
        await self._client.logout()
        self.action_back()

    @on(ListView.Selected, item="#create_game")
    def create_game(self) -> None:
        self.app.push_screen(screens.CreateGame())

    @on(ListView.Selected, item="#join_game")
    async def join_game(self) -> None:
        await self.app.push_screen(screens.JoinGame())

    @on(ListView.Selected, item="#stats")
    async def show_statistics(self) -> None:
        self.loading = True  # noqa

        try:
            statistics = await self._client.fetch_statistics()
            await self.app.push_screen(screens.Statistics(data=statistics))
        except ClientError:
            self.notify(
                "Cannot load statistics", title="Loading error", severity="error", timeout=5
            )
        finally:
            self.loading = False  # noqa

    async def update_online_count(self, count: int) -> None:
        self.query_one(LobbyHeader).players_online = count

    async def update_ingame_count(self, count: int) -> None:
        self.query_one(LobbyHeader).players_ingame = count

    async def fetch_player_count(self) -> None:
        try:
            count = await self._client.fetch_players_online()
        except ClientError as exc:
            logger.warning("Cannot fetch online players count. {exc}", exc=exc)
        else:
            await self.update_online_count(count.total)
            await self.update_ingame_count(count.ingame)

    async def subscribe_to_player_count(self) -> None:
        try:
            subscription = await self._client.players_subscribe()
        except ClientError as exc:
            logger.warning("Cannot subscribe to players updates. {exc}", exc=exc)
        else:
            subscription.on_online_changed(self.update_online_count)
            subscription.on_ingame_changed(self.update_ingame_count)
            self._player_subscription = subscription

    async def unsubscribe_from_player_count(self) -> None:
        try:
            await self._client.players_unsubscribe()
        except ClientError as exc:
            logger.warning("Cannot unsubscribe from online count. {exc}", exc=exc)

    def handle_connection_lost(self) -> None:
        async def handle_connection_established() -> None:
            logger.debug("Connection restored, resubscribe to player count updates..")
            self._client.remove_listener(
                ConnectionEvent.CONNECTION_IMPOSSIBLE, handle_connection_impossible
            )
            await self._setup_player_count_updates()

        def handle_connection_impossible() -> None:
            logger.debug("Resubscription to player count updates is impossible.")
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

    async def _setup_player_count_updates(self) -> None:
        await self.subscribe_to_player_count()
        await self.fetch_player_count()
