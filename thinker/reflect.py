def light_reflect(reply: str) -> str:
    txt = (reply or "").strip()
    if len(txt) > 600:
        txt = txt[:580].rstrip() + "..."
    return txt
