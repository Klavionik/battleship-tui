import argparse
import asyncio
import csv
import secrets

from rich.progress import track

from battleship.server.auth import Auth0API
from battleship.server.config import Config

parser = argparse.ArgumentParser()
parser.add_argument("--start", default=0, type=int)
parser.add_argument("--stop", default=100, type=int)

FILL_VALUE = object()


def generate_password() -> str:
    return secrets.token_urlsafe(7)


async def create_load_testing_users(start: int, stop: int) -> None:
    config = Config()
    api = Auth0API.from_config(config)
    next_pair = []

    with (
        open("virtual_users.csv", mode="a") as vus_fh,
        open("load_testing_accounts.csv", mode="a") as accounts_fh,
    ):
        vus_writer = csv.writer(vus_fh)
        accounts_writer = csv.writer(accounts_fh)

        for i in track(range(start, stop), description="Creating users..."):
            email = f"loadtesting{i}@battleship.invalid"
            nickname = f"loadtesting{i}"
            password = generate_password()
            user = await api.signup(email, nickname, password)
            user_id = "auth0|" + user["_id"]
            await api.add_roles(user_id, config.AUTH0_ROLES["guest"])
            accounts_writer.writerow([user_id, nickname, password])
            next_pair.append(f"{nickname}:{password}")

            if len(next_pair) == 2:
                vus_writer.writerow(next_pair)
                next_pair.clear()

            await asyncio.sleep(0.1)


if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(create_load_testing_users(args.start, args.stop))
