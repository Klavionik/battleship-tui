import argparse
import asyncio
import signal

from loguru import logger
from websockets import serve  # type: ignore[attr-defined]

from battleship.server.connections import ConnectionManager
from battleship.server.players import Players
from battleship.server.sessions import Sessions

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="localhost")
parser.add_argument("--port", type=int, default=8000)


async def run_server(host: str, port: int) -> None:
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    sessions = Sessions()
    players = Players()
    handler = ConnectionManager(sessions, players)

    async with serve(handler, host=host, port=port):
        logger.info(f"Serving at {host}:{port}")
        await stop

    for connection in handler.connections:
        logger.info(f"Closing connection with {connection.local_address}")
        await connection.close()

        logger.info("Server shut down.")


if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(run_server(args.host, args.port))
