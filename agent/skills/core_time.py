from typing import Dict, Any
from .registry import register
from datetime import datetime

try:
    from firebase_db import get_timezone  # from app/
except Exception:
    def get_timezone(): return 'Asia/Kolkata'

@register('get_time')
def get_time(_: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from zoneinfo import ZoneInfo
        tz = get_timezone() or 'Asia/Kolkata'
        now = datetime.now(ZoneInfo(tz))
        return {'now_human': now.strftime('%A, %d %B %Y, %I:%M %p'), 'tz': tz}
    except Exception:
        now = datetime.utcnow()
        return {'now_human': now.strftime('%A, %d %B %Y, %I:%M %p'), 'tz': 'UTC'}
