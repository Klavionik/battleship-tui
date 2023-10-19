class Player:
    def __init__(self, nickname: str | None):
        self.nickname = nickname or "Guest"


class Players:
    def __init__(self) -> None:
        self._players: dict[str, Player] = {}

    def add_player(self, nickname: str) -> Player:
        player = Player(nickname)
        self._players[nickname] = player
        return player

    def get_player(self, nickname: str) -> Player:
        return self._players[nickname]

    def list_players(self) -> list[Player]:
        return list(self._players.values())

    def remove_player(self, nickname: str) -> None:
        self._players.pop(nickname, None)


players = Players()
