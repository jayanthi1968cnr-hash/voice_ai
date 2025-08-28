from typing import Dict, Any
from .registry import register

try:
    from firebase_db import save_fact, add_reminder, set_assistant_name  # from app/
except Exception:
    def save_fact(k, v): ...
    def add_reminder(t, when): ...
    def set_assistant_name(n): ...

@register('save_fact')
def save_fact_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    key = (args.get('key') or '').strip().lower().replace(' ', '_')
    val = (args.get('value') or '').strip()
    if not key or not val: return {'ok': False, 'error': 'missing key/value'}
    save_fact(key, val); return {'ok': True}

@register('add_reminder')
def add_reminder_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    text = (args.get('text') or '').strip()
    when_iso = (args.get('when_iso') or '').strip()
    if not text or not when_iso: return {'ok': False, 'error': 'missing text/when'}
    add_reminder(text, when_iso); return {'ok': True}

@register('set_assistant_name')
def set_assistant_name_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    name = (args.get('name') or '').strip()
    if not name: return {'ok': False, 'error': 'missing name'}
    set_assistant_name(name); return {'ok': True}
