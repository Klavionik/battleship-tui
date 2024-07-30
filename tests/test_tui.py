import functools

import pytest

from battleship.tui import BattleshipApp, Config, di

TERMINAL_SIZE = (120, 35)
RELATIVE_APP_PATH = "../battleship/tui/app.py"


@pytest.fixture(scope="session")
def test_config():
    config = Config(
        server_url="http://locahost:9000",
        credentials_provider="battleship.client.credentials:DummyCredentialsProvider",
        game_settings_provider="battleship.tui.settings:InMemorySettingsProvider",
    )
    return config


@pytest.fixture(autouse=True, scope="session")
def test_di(test_config):
    di.configure(test_config)
    yield


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
    assert snap_compare_sized(press=["down", "down", "enter"])


@pytest.mark.snap
def test_singleplayer_screen_snapshot(snap_compare_sized):
    assert snap_compare_sized(press=["enter"])


@pytest.mark.snap
def test_multiplayer_screen_snapshot(snap_compare_sized):
    assert snap_compare_sized(press=["down", "enter"])


@pytest.mark.snap
def test_singleplayer_game_screen_snapshot(snap_compare_sized):
    assert snap_compare_sized(press=["enter", *["tab"] * 4, "enter"])


@pytest.mark.snap
def test_main_screen_snapshot(snap_compare_sized):
    assert snap_compare_sized()
