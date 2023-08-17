import argparse

from websockets.sync.server import ServerConnection, serve

parser = argparse.ArgumentParser()
parser.add_argument("--host", "-h", type=str, default="localhost")
parser.add_argument("--port", "-p", type=int, default=8000)


def handle_connection(connection: ServerConnection) -> None:
    pass


def run_server(host: str, port: int) -> None:
    with serve(handle_connection, host=host, port=port) as server:
        server.serve_forever()


if __name__ == "__main__":
    args = parser.parse_args()
    run_server(args.host, args.port)
