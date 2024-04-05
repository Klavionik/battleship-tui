import argparse
import asyncio
import csv
import io
from typing import Sequence

from rich.progress import track

from battleship.server.auth import Auth0API
from battleship.server.config import Config

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--users", action="append")
group.add_argument("--users-file", type=argparse.FileType())


def parse_users_file(file: io.TextIOWrapper) -> list[str]:
    reader = csv.reader(file)
    return ["auth0|" + line[0] for line in reader]


async def delete_load_testing_users(user_ids: Sequence[str]) -> None:
    config = Config()
    api = Auth0API.from_config(config)

    for user_id in track(user_ids, description="Deleting users..."):
        await api.delete_user(user_id)
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    args = parser.parse_args()

    if users_file := args.users_file:
        users = parse_users_file(users_file)
    else:
        users = args.users

    asyncio.run(delete_load_testing_users(users))
