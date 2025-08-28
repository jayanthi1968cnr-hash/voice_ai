# memory_catcher.py
# Pure NLP parser for user memory commands.
# No external imports (no cfg, no firebase). Returns a structured bundle
# that main.py can persist using firebase_db.

import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional


__all__ = ["catch_memory"]


# ------------- utilities -------------
def _norm_key(s: str) -> str:
    """Normalize fact keys to a safe form (unused by main; kept for internal checks)."""
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s[:80] or "key"


def _split_list(s: str) -> List[str]:
    """Split 'cats, dogs and birds' -> ['cats', 'dogs', 'birds']."""
    if not s:
        return []
    s = re.sub(r"\s+and\s+", ",", s, flags=re.I)
    parts = [p.strip(" .,'-") for p in s.split(",")]
    return [p for p in parts if p]


# Simple timezone normalizer for common names/abbreviations
_TZ_MAP = {
    "ist": "Asia/Kolkata",
    "indian": "Asia/Kolkata",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "est": "America/New_York",
    "edt": "America/New_York",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "gmt": "Etc/GMT",
    "utc": "UTC",
}


def _norm_tz(s: str) -> Optional[str]:
    """Return an IANA tz string if recognized, else None."""
    s = (s or "").strip()
    if not s:
        return None
    key = s.lower().replace("time", "").replace("zone", "").strip()
    if key in _TZ_MAP:
        return _TZ_MAP[key]
    # Allow full IANA zone strings like "Asia/Kolkata"
    if re.match(r"^[A-Za-z]+/[A-Za-z_]+$", s):
        return s
    return None


def _parse_when_iso(phrase: str) -> Optional[str]:
    """Parse simple natural times to ISO (local naive)."""
    phrase = (phrase or "").strip().lower()
    now = datetime.now()

    # in X minutes/hours
    m = re.search(r"in\s+(\d{1,3})\s*(minute|minutes|min|hour|hours|hr|hrs)", phrase)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(minutes=n) if "min" in unit or "minute" in unit else timedelta(hours=n)
        return (now + delta).replace(microsecond=0).isoformat()

    # tomorrow at hh(:mm)?(am|pm)?
    m = re.search(r"tomorrow(?:\s+at)?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", phrase)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2) or 0); ap = (m.group(3) or "").lower()
        if ap == "pm" and hh < 12: hh += 12
        if ap == "am" and hh == 12: hh = 0
        dt = (now + timedelta(days=1)).replace(hour=hh, minute=mm, second=0, microsecond=0)
        return dt.isoformat()

    # at hh(:mm)?(am|pm)?
    m = re.search(r"(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)", phrase)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2) or 0); ap = (m.group(3) or "").lower()
        if ap == "pm" and hh < 12: hh += 12
        if ap == "am" and hh == 12: hh = 0
        dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return dt.isoformat()

    # 24h “at 14:30”
    m = re.search(r"(?:at\s+)?([01]?\d|2[0-3]):([0-5]\d)", phrase)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2))
        dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return dt.isoformat()

    return None


# ------------- patterns -------------
NAME_PATTS = [
    re.compile(r"\bmy\s+name\s+is\s+([A-Za-z][\w .'\-]{1,60})", re.I),
    re.compile(r"\bname\s+is\s+([A-Za-z][\w .'\-]{1,60})", re.I),
    re.compile(r"\bcall\s+me\s+([A-Za-z][\w .'\-]{1,60})", re.I),
    re.compile(r"\byou\s+can\s+call\s+me\s+([A-Za-z][\w .'\-]{1,60})", re.I),
]

FACT_PH_PREFIX = re.compile(r"\b(?:remember|save|set)\b", re.I)

FACT_IS_PAT = re.compile(
    r"(?:my\s+)?([A-Za-z][\w '\-]{1,40})\s*(?:is|=|to|are)\s+([^.;,\n]{1,100})",
    re.I,
)

LIKE_PAT = re.compile(
    r"\b(?:remember|save).*?\bi\s+(?:like|love|hate)\s+([^.;\n]{1,100})",
    re.I
)

TZ_PATTS = [
    re.compile(r"\b(?:set\s+)?time\s*zone\s+(?:to\s+)?([A-Za-z/_-]{2,40})", re.I),
    re.compile(r"\b(?:my\s+)?timezone\s+(?:is|=)\s+([A-Za-z/_-]{2,40})", re.I),
    re.compile(r"\b(?:set\s+)?tz\s+(?:to\s+)?([A-Za-z/_-]{2,40})", re.I),
    re.compile(r"\b(?:use|switch\s+to)\s+([A-Za-z/_-]{2,40})\s+time\b", re.I),
]

REMIND_PATTS = [
    # remind me to TASK at WHEN
    re.compile(r"\bremind\s+me\s+to\s+(.+?)\s+(?:at|on|in)\s+(.+)", re.I),
    # remind me at WHEN to TASK
    re.compile(r"\bremind\s+me\s+(?:at|on|in)\s+(.+?)\s+to\s+(.+)", re.I),
]

EVENT_PATTS = [
    re.compile(r"\badd\s+event\s+(.+?)\s+(?:on|at)\s+([0-9]{4}-[0-9]{2}-[0-9]{2}|tomorrow|today)\b", re.I),
]

MOOD_PATTS = [
    re.compile(r"\blog\s+mood\s+([A-Za-z]{2,20})(?:\s*[:\-]\s*(.+))?$", re.I),
    re.compile(r"\bremember\s+my\s+mood\s+is\s+([A-Za-z]{2,20})(?:\s*[:\-]\s*(.+))?$", re.I),
]


# ------------- main catcher -------------
def catch_memory(user_text: str) -> Dict[str, object]:
    """
    Parse natural memory commands into a structured bundle.

    Returns:
      {
        'facts': List[(key, value)]                 # e.g. [("name","Shiva"), ("wifi password","tiger123")]
        'timezone': Optional[str],                  # e.g. "Asia/Kolkata"
        'reminders': List[{'text','when_iso'}],     # one simple reminder
        'events': List[{'title','date','emotion'}],
        'moods': List[{'mood','note'}],
        'acks': List[str]                           # human-friendly confirmations
      }
    """
    text = (user_text or "").strip()
    out: Dict[str, object] = {
        "facts": [],
        "timezone": None,
        "reminders": [],
        "events": [],
        "moods": [],
        "acks": [],
    }

    # --- name (works even without "remember") ---
    for p in NAME_PATTS:
        m = p.search(text)
        if m:
            name = m.group(1).strip(" .,'-")
            if name:
                out["facts"].append(("name", name))
                out["acks"].append(f"name = {name}")
                break

    # --- likes/loves/hates list (only if remember/save present) ---
    lm = LIKE_PAT.search(text)
    if lm:
        things = _split_list(lm.group(1))
        if things:
            val = ", ".join(things)
            out["facts"].append(("likes", val))
            out["acks"].append(f"likes = {val}")

    # --- generic facts "remember/set my X is Y", support multiple ---
    if FACT_PH_PREFIX.search(text):
        for m in FACT_IS_PAT.finditer(text):
            key_raw = m.group(1).strip(" .,'-")
            val_raw = m.group(2).strip(" .,'-")
            if not key_raw or not val_raw:
                continue
            if re.search(r"\bare\b", m.group(0), flags=re.I):
                val_parts = _split_list(val_raw)
                val = ", ".join(val_parts) if val_parts else val_raw
            else:
                val = val_raw
            # Return the human key; main.py will normalize for Firestore
            out["facts"].append((key_raw, val))
            out["acks"].append(f"{key_raw.lower()} = {val}")

    # --- timezone updates ---
    for p in TZ_PATTS:
        m = p.search(text)
        if m:
            tz = _norm_tz(m.group(1))
            if tz:
                out["timezone"] = tz
                out["acks"].append(f"timezone = {tz}")
                break

    # --- reminders (two common word orders) ---
    for p in REMIND_PATTS:
        m = p.search(text)
        if m:
            if p.pattern.startswith(r"\bremind\s+me\s+to"):
                task, when_str = m.group(1), m.group(2)
            else:
                when_str, task = m.group(1), m.group(2)
            when_iso = _parse_when_iso(when_str)
            if task and when_iso:
                out["reminders"].append({"text": task.strip(), "when_iso": when_iso})
                out["acks"].append(f"reminder '{task.strip()}' @ {when_iso}")
            break  # keep simple (one reminder)

    # --- events ---
    for p in EVENT_PATTS:
        m = p.search(text)
        if m:
            title = m.group(1).strip(" '")
            date_tok = m.group(2).lower()
            if date_tok == "today":
                date_iso = datetime.now().replace(microsecond=0).isoformat()
            elif date_tok == "tomorrow":
                date_iso = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
            else:
                date_iso = date_tok  # yyyy-mm-dd as given
            out["events"].append({"title": title, "date": date_iso, "emotion": ""})
            out["acks"].append(f"event '{title}' on {date_iso}")
            break

    # --- moods ---
    for p in MOOD_PATTS:
        m = p.search(text)
        if m:
            mood = (m.group(1) or "").strip()
            note = (m.group(2) or "").strip()
            out["moods"].append({"mood": mood, "note": note})
            out["acks"].append(f"mood = {mood}" + (f" ({note})" if note else ""))
            break

    return out
