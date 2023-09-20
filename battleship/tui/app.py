import asyncio

from textual.app import App


class BattleshipApp(App[None]):
    BINDINGS = [("ctrl+q", "quit", "Quit"), ("F1", "help", "Help")]
    TITLE = "Battleship"
    SUB_TITLE = "The Game"


async def _run() -> None:
    app = BattleshipApp()
    await app.run_async()


def run() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    run()
