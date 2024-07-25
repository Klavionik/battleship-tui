from string import Template

from battleship.shared.models import Session

MAX_GAME_NAME = 20


def truncate_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text

    text = text[:max_length]
    text = text + "..."
    return text


def format_duration(duration_secs: int) -> str:
    minutes = duration_secs // 60
    seconds = duration_secs % 60

    if minutes > 0:
        return f"{minutes} min {seconds} s"
    return f"{seconds} s"


def format_session(template: str, session: Session) -> str:
    salvo_mode = "Yes" if session.salvo_mode else "No"
    adjacent_ships = "Yes" if not session.no_adjacent_ships else "No"
    firing_order = session.firing_order.replace("_", " ").capitalize()
    return Template(template).substitute(
        name=truncate_text(session.name, MAX_GAME_NAME),
        salvo_mode=salvo_mode,
        firing_order=firing_order,
        roster=session.roster.capitalize(),
        adjacent_ships=adjacent_ships,
    )
