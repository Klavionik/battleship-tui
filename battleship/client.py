import argparse

from websockets.sync.client import connect

parser = argparse.ArgumentParser()
parser.add_argument("--host", "-h", type=str, default="localhost")
parser.add_argument("--port", "-p", type=int, default=8000)


def run_client(host: str, port: int) -> None:
    with connect(f"ws://{host}:{port}") as ws:  # noqa: F841
        pass


if __name__ == "__main__":
    args = parser.parse_args()
    run_client(args.host, args.port)
