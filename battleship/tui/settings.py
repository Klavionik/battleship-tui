from battleship.shared.models import BaseModel


class Settings(BaseModel):
    player_name: str = "Player"
    fleet_color: str = "#FFFFFF"
    enemy_fleet_color: str = "#AAAAAA"
    language: str = "English"

    @property
    def language_options(self) -> list[str]:
        return ["English"]
