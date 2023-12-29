import pytest

from battleship.tui import BattleshipApp, Config, configure_injection


@pytest.fixture
def test_config():
    config = Config(
        server_url="http://locahost:9000",
        credentials_provider="battleship.client.credentials:dummy_credentials_provider",
        game_settings_provider="battleship.tui.settings:in_memory_settings_provider",
    )
    return config


async def test_quits_with_ctrl_q(test_config):
    configure_injection(test_config)
    app = BattleshipApp()

    async with app.run_test() as pilot:
        await pilot.press("ctrl+q")

    assert app.return_code == 0
