import functools

import inject
import pytest

from battleship.tui import BattleshipApp, Config, configure_injection

TERMINAL_SIZE = (120, 35)
RELATIVE_APP_PATH = "../battleship/tui/app.py"


@pytest.fixture(scope="session")
def test_config():
    config = Config(
        server_url="http://locahost:9000",
        credentials_provider="battleship.client.credentials:dummy_credentials_provider",
        game_settings_provider="battleship.tui.settings:in_memory_settings_provider",
    )
    return config


@pytest.fixture(autouse=True, scope="session")
def test_di(test_config):
    configure_injection(test_config)
    yield
    inject.clear()


@pytest.fixture
def snap_compare_sized(snap_compare):
    compare = functools.partial(
        snap_compare,
        app_path=RELATIVE_APP_PATH,
        terminal_size=TERMINAL_SIZE,
    )
    return compare


async def test_quits_with_ctrl_q():
    app = BattleshipApp()

    async with app.run_test() as pilot:
        await pilot.press("ctrl+q")

    assert app.return_code == 0


@pytest.mark.snap
def test_settings_screen_snapshot(snap_compare_sized):
    snap_compare_sized(press=["down", "down", "enter"])


@pytest.mark.snap
def test_singleplayer_screen_snapshot(snap_compare_sized):
    snap_compare_sized(press=["enter"])


@pytest.mark.snap
def test_multiplayer_screen_snapshot(snap_compare_sized):
    snap_compare_sized(press=["down", "enter"])


@pytest.mark.snap
def test_singleplayer_game_screen_snapshot(snap_compare_sized):
    snap_compare_sized(press=["enter", *["tab"] * 4, "enter"])
