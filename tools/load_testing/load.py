"""
Simulates concurrent multiplayer game sessions.

Reads host-player pairs from the command line or from a CSV file
and runs N asyncio tasks, each representing a game session.

During a game session, both users execute following steps.

1. Log in and establish a WS connection.
2. Create a game (if host)/join a hame (if player).
3. Make moves.
4. Disconnect.
"""

import argparse
import asyncio
import csv
import functools
import io
import random
import time
from collections.abc import Awaitable, Iterator
from dataclasses import dataclass
from itertools import cycle
from typing import Sequence

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
)

from battleship.client import Client
from battleship.client.credentials import DummyCredentialsProvider
from battleship.shared.events import ServerEvent

RUN_TIMEOUT = 600  # 10 minutes.

console = Console()
progress = Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    transient=True,
    console=console,
)


@dataclass
class VirtualUser:
    nickname: str
    password: str


def virtual_user(string: str) -> VirtualUser:
    nickname, password = string.split(":")
    return VirtualUser(nickname, password)


def parse_users_file(file: io.TextIOWrapper) -> list[tuple[VirtualUser, VirtualUser]]:
    reader = csv.reader(file)
    return [(virtual_user(pair[0]), virtual_user(pair[1])) for pair in reader]


parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--server-url",
    default="http://localhost:8000",
    help="Target server URL",
)

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument(
    "--users",
    type=virtual_user,
    nargs=2,
    action="append",
    help="Pairs of host-player",
    metavar="nickname:password",
)
group.add_argument(
    "--users-file",
    type=argparse.FileType(),
    help="CSV file that contains host-player pairs",
)


HOST_SHIP_POSITIONS = [
    ["B2", "C2", "D2", "E2", "F2"],
    ["I5", "I6", "I7", "I8"],
    ["B9", "C9", "D9"],
    ["C5", "D5", "E5"],
    ["G10", "H10"],
]

PLAYER_SHIP_POSITIONS = [
    ["B8", "C8", "D8", "E8", "F8"],
    ["C2", "D2", "E2", "F2"],
    ["H4", "H5", "H6"],
    ["B5", "C5", "D5"],
    ["J8", "J9"],
]

HOST_TARGETS = [
    "C2",
    "D2",
    "B4",
    "E6",
    "E2",
    "F2",
    "C8",
    "C7",
    "C9",
    "A8",
    "D8",
    "F8",
    "E8",
    "B8",
    "H5",
    "H6",
    "H4",
    "I8",
    "G10",
    "C10",
    "J5",
    "I2",
    "E4",
    "C1",
    "E3",
    "C5",
    "D5",
    "E5",
    "B5",
    "H1",
    "J4",
    "J8",
    "J9",
]

PLAYER_TARGETS = [
    "C3",
    "F6",
    "H2",
    "C8",
    "G4",
    "C1",
    "F8",
    "I7",
    "G9",
    "B6",
    "C10",
    "I8",
    "I9",
    "I6",
    "I5",
    "D5",
    "D6",
    "D4",
    "C5",
    "E5",
    "F1",
    "J1",
    "H10",
    "G10",
    "A8",
    "D9",
    "D10",
    "D8",
    "C9",
    "B9",
    "G3",
    "J3",
    "J7",
]


async def delay(duration: float | None = None) -> None:
    if duration is None:
        duration = random.randint(1, 3)

    await asyncio.sleep(duration)


async def login(client: Client, nickname: str, password: str) -> None:
    await client.login(nickname, password)


async def connect(client: Client) -> None:
    await client.connect()


async def disconnect(client: Client) -> None:
    await client.disconnect()


async def players_subscribe(client: Client) -> None:
    await client.players_subscribe()


async def fetch_players_online(client: Client) -> None:
    await client.fetch_players_online()


async def players_unsubscribe(client: Client) -> None:
    await client.players_unsubscribe()


async def sessions_subscribe(client: Client) -> None:
    await client.sessions_subscribe()


async def sessions_unsubscribe(client: Client) -> None:
    await client.sessions_unsubscribe()


async def create_session(
    client: Client,
    name: str = "load_testing",
    roster: str = "classic",
    firing_order: str = "alternately",
    salvo: bool = False,
) -> str:
    session = await client.create_session(name, roster, firing_order, salvo)
    return session.id


async def fetch_sessions(client: Client) -> None:
    await client.fetch_sessions()


async def join_game(client: Client, session_id: str) -> None:
    await client.join_game(session_id)


async def spawn_ship(client: Client, ship_id: str, position: Sequence[str]) -> None:
    await client.spawn_ship(ship_id, position)


async def fire(client: Client, position: Sequence[str]) -> None:
    await client.fire(position)


async def wait_sequence(sequence: Sequence[Awaitable[None]]) -> None:
    for awaitable in sequence:
        await awaitable


async def load(
    name: str, server_url: str, host_user: VirtualUser, player_user: VirtualUser, task_id: TaskID
) -> None:
    player = Client(server_url=server_url, credentials_provider=DummyCredentialsProvider())
    host = Client(server_url=server_url, credentials_provider=DummyCredentialsProvider())

    pre_host = [
        login(host, nickname=host_user.nickname, password=host_user.password),
        connect(host),
        delay(1),
        players_subscribe(host),
        fetch_players_online(host),
        delay(1),
        players_unsubscribe(host),
    ]

    pre_player = [
        login(player, nickname=player_user.nickname, password=player_user.password),
        connect(player),
        delay(1),
        players_subscribe(player),
        fetch_players_online(player),
        delay(1),
        sessions_subscribe(player),
        fetch_sessions(player),
        players_unsubscribe(player),
    ]

    pre_host_task = asyncio.create_task(wait_sequence(pre_host))
    pre_player_task = asyncio.create_task(wait_sequence(pre_player))

    await asyncio.gather(pre_player_task, pre_host_task)

    progress.update(task_id, description=f"{name} | Spawn ships", advance=1)

    await delay(2)

    session_id = await create_session(host)
    await join_game(player, session_id)

    await delay()

    roster_items = (await host.get_roster("classic")).items

    spawn_host = []
    spawn_player = []

    for i in range(len(roster_items)):
        spawn_host.append(delay(1.5))
        spawn_host.append(spawn_ship(host, roster_items[i].id, HOST_SHIP_POSITIONS[i]))

        spawn_player.append(delay(1.5))
        spawn_player.append(spawn_ship(player, roster_items[i].id, PLAYER_SHIP_POSITIONS[i]))

    spawn_host_task = asyncio.create_task(wait_sequence(spawn_host))
    spawn_player_task = asyncio.create_task(wait_sequence(spawn_player))

    await asyncio.gather(spawn_host_task, spawn_player_task)

    progress.update(task_id, description=f"{name} | Play game", advance=1)

    awaiting_move_event = asyncio.Event()
    first_shooter = ""

    def discover_first_shooter(payload: dict[str, str]) -> None:
        nonlocal first_shooter
        first_shooter = payload["actor"]
        awaiting_move_event.set()

    host.add_listener(ServerEvent.AWAITING_MOVE, discover_first_shooter, once=True)
    await awaiting_move_event.wait()

    if first_shooter == host.nickname:
        targets = zip(HOST_TARGETS, PLAYER_TARGETS)
        clients = cycle((host, player))
    else:
        targets = zip(PLAYER_TARGETS, HOST_TARGETS)
        clients = cycle((player, host))

    def iterate_moves() -> Iterator[tuple[Client, str]]:
        for target, next_target in targets:
            yield next(clients), target
            yield next(clients), next_target

    for client, move in iterate_moves():
        await delay()
        await fire(client, [move])

    progress.update(task_id, description=f"{name} | Disconnect", advance=1)

    await delay()
    await disconnect(host)
    await disconnect(player)

    progress.update(task_id, description=f"{name} | Finished", advance=1)


def indicate_error_cb(tsk: asyncio.Task[None], task_id: TaskID, name: str) -> None:
    try:
        tsk.result()
    except Exception:
        progress.update(task_id, description=f"[red]{name} | Error", completed=4)
        progress.stop_task(task_id)


async def main(server_url: str, virtual_users: list[tuple[VirtualUser, VirtualUser]]) -> int:
    exit_code = 0
    session_tasks = []

    for host, player in virtual_users:
        name = f"{host.nickname} vs. {player.nickname}"
        task_id = progress.add_task(description=f"{name} | Connect", total=4)
        done_cb = functools.partial(indicate_error_cb, task_id=task_id, name=name)
        task = asyncio.create_task(load(name, server_url, host, player, task_id))
        task.add_done_callback(done_cb)
        session_tasks.append(task)

    console.log(f"[bold]Running {len(session_tasks)} game sessions.")
    start = time.monotonic()

    with progress:
        for future in asyncio.as_completed(session_tasks, timeout=RUN_TIMEOUT):
            try:
                await future
            except Exception:
                exit_code = 1

    elapsed = time.monotonic() - start

    console.log(f"[bold]All game sessions finished in {int(elapsed)} s.")

    if exit_code == 1:
        console.log("[red]There were some error(s) during the execution.")
    else:
        console.log("[green]Successfully.")

    return exit_code


if __name__ == "__main__":
    args = parser.parse_args()

    if users_file := args.users_file:
        users = parse_users_file(users_file)
    else:
        users = args.users

    raise SystemExit(asyncio.run(main(args.server_url, users)))
