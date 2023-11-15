from string import Template

from battleship.shared.models import Session


def format_duration(duration_secs: int) -> str:
    minutes = duration_secs // 60
    seconds = duration_secs % 60

    if minutes > 0:
        return f"{minutes} min {seconds} s"
    return f"{seconds} s"


def format_session(template: str, session: Session) -> str:
    salvo_mode = "Yes" if session.salvo_mode else "No"
    firing_order = session.firing_order.replace("_", " ").capitalize()
    return Template(template).substitute(
        name=session.name,
        salvo_mode=salvo_mode,
        firing_order=firing_order,
        roster=session.roster.capitalize(),
    )
