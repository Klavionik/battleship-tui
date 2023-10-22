import dataclasses


@dataclasses.dataclass
class SessionCreate:
    name: str
    roster: str
    firing_order: str
    salvo_mode: bool

    def as_dict(self) -> dict[str, str | bool]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class GuestUser:
    display_name: str
    access_token: str
