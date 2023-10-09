from pathlib import Path

RESOURCES_DIR = Path(__file__).parent / "resources"


def get_resource(filename: str) -> Path:
    return Path(RESOURCES_DIR / filename)
