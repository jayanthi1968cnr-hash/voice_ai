# context_bridge.py
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
from typing import Tuple, List

from config import cfg
from firebase_db import (
    load_facts, get_reminders, get_timezone
)

def _now_str() -> Tuple[str, str]:
    # Prefer timezone from Firestore meta; fallback to env/default
    tz = get_timezone() or "Asia/Kolkata"
    try:
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        # Fallback if OS tzdata missing
        now = datetime.utcnow()
        tz = "UTC"
    iso_full = now.isoformat(timespec="seconds")
    human = now.strftime("%A, %d %B %Y, %I:%M %p")
    return f"{human} ({tz})", iso_full

def _format_reminders(limit: int = 5) -> List[str]:
    items = get_reminders() or []
    # items are [{"message": str, "time": str, ...}], sort by time if ISO-like
    def _key(it):
        t = it.get("time") or it.get("whenISO") or ""
        return t
    items = sorted(items, key=_key)[:limit]
    out = []
    for it in items:
        msg = (it.get("message") or it.get("text") or "").strip()
        when = (it.get("time") or it.get("whenISO") or "").strip()
        out.append(f"- {msg} @ {when}")
    return out

def build_grounding_snapshot() -> str:
    """
    Returns a short string you can inject as SYSTEM or prepend to USER.
    Keep it compact to avoid token bloat.
    """
    human_now, iso_now = _now_str()
    facts = load_facts() or {}
    reminders = _format_reminders()

    lines = []
    lines.append("GROUND TRUTH (authoritative; do not hallucinate):")
    lines.append(f"- Now: {human_now}")
    if facts:
        lines.append("- Facts:")
        for k, v in list(facts.items())[:20]:  # cap to avoid bloat
            lines.append(f"  • {k}: {v}")
    if reminders:
        lines.append("- Upcoming reminders:")
        lines += [f"  {r}" for r in reminders]
    return "\n".join(lines)
