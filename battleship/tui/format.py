def format_duration(duration_secs: int) -> str:
    minutes = duration_secs // 60
    seconds = duration_secs % 60

    if minutes > 0:
        return f"{minutes} min {seconds} s"
    return f"{seconds} s"
