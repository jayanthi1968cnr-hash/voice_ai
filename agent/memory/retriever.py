from typing import Dict, Any
try:
    from firebase_db import load_facts, get_reminders, get_timezone, get_assistant_name
except Exception:
    def load_facts(): return {}
    def get_reminders(): return []
    def get_timezone(): return 'Asia/Kolkata'
    def get_assistant_name(): return None

from datetime import datetime

def build_grounding() -> Dict[str, Any]:
    facts = load_facts() or {}
    reminders = get_reminders() or []
    tz = get_timezone() or 'Asia/Kolkata'
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        now = datetime.utcnow(); tz = 'UTC'

    return {
        'now_human': now.strftime('%A, %d %B %Y, %I:%M %p'),
        'tz': tz,
        'assistant_name': get_assistant_name() or None,
        'user_name': facts.get('name') or facts.get('user name'),
        'facts': facts,
        'reminders': reminders[:8],
        'episodes': []  # TODO: add episodic retrieval
    }
