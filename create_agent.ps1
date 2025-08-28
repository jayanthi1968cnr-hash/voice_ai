# create_agent.ps1
$root = "agent"   # change to "Eagent" if you prefer

function Write-File($Path, $Content) {
  $dir = Split-Path $Path
  if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  Set-Content -Path $Path -Value $Content -Encoding UTF8
}

# Folders
New-Item -ItemType Directory -Path "$root" -Force | Out-Null
New-Item -ItemType Directory -Path "$root\skills" -Force | Out-Null
New-Item -ItemType Directory -Path "$root\memory" -Force | Out-Null

# __init__.py
Write-File "$root\__init__.py" @"
# $root package
__all__ = ["planner", "affect", "schemas", "safety", "utils"]
"@

# schemas.py
Write-File "$root\schemas.py" @"
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List

class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)

class Plan(BaseModel):
    intent: str = "respond"
    confidence: float = 0.5
    tool_call: Optional[ToolCall] = None
    response_hint: str = ""

    @validator("confidence")
    def _clamp(cls, v): return max(0.0, min(1.0, float(v)))

class Grounding(BaseModel):
    now_human: str
    tz: str
    assistant_name: Optional[str] = None
    user_name: Optional[str] = None
    facts: Dict[str, str] = Field(default_factory=dict)
    reminders: List[Dict[str, Any]] = Field(default_factory=list)
    episodes: List[str] = Field(default_factory=list)

class Observation(BaseModel):
    tool: Optional[str] = None
    result: Dict[str, Any] = Field(default_factory=dict)
"@

# affect.py
Write-File "$root\affect.py" @"
import re

def detect_affect(text: str) -> str:
    t = (text or '').lower()
    if re.search(r'\b(angry|annoyed|frustrated|wtf)\b', t): return 'angry'
    if re.search(r'\b(sad|down|tired|exhausted)\b', t): return 'sad'
    if re.search(r'\b(thanks|great|awesome|nice|cool)\b', t): return 'positive'
    return 'neutral'
"@

# utils.py
Write-File "$root\utils.py" @"
import json

def extract_first_json(s: str) -> dict:
    start = s.find('{'); end = s.rfind('}')
    if start == -1 or end == -1 or end <= start: return {}
    try:
        return json.loads(s[start:end+1])
    except Exception:
        return {}
"@

# safety.py
Write-File "$root\safety.py" @"
def self_check(reply: str) -> str:
    # TODO: add factual/safety checks or call a verifier model
    return reply
"@

# planner.py
Write-File "$root\planner.py" @"
import json
from typing import Dict, Any
from .schemas import Plan, ToolCall
from .utils import extract_first_json
from llm import ask_llm_full  # ensure your app/ is on PYTHONPATH

SYSTEM = (
  'You are a planning controller for a voice assistant. '
  'Return JSON only. '
  'Schema: {\"intent\": str, \"confidence\": float, \"tool_call\": {\"name\": str, \"args\": object} | null, \"response_hint\": str} '
  'Valid tools: get_time, save_fact, add_reminder, set_assistant_name '
  'Rules: '
  '- If user says \"your name is X\"  set_assistant_name. '
  '- If storing a user fact  save_fact. '
  '- If reminder phrasing  add_reminder (include when_iso if provided). '
  '- If simple Q&A  tool_call=null and response_hint is a short reply. '
  '- JSON ONLY, no markdown.'
)

def plan_turn(user_text: str, grounding: Dict[str, Any], affect: str = 'neutral') -> Plan:
    g = json.dumps(grounding, ensure_ascii=False)
    prompt = f"{SYSTEM}\nGROUNDING:{g}\nAFFECT:{affect}\nUSER:{user_text}\nPLAN:"
    raw = ask_llm_full(prompt) or '{}'
    obj = extract_first_json(raw)
    tool = obj.get('tool_call')
    tc = ToolCall(**tool) if isinstance(tool, dict) and 'name' in tool else None
    return Plan(
        intent=obj.get('intent', 'respond'),
        confidence=obj.get('confidence', 0.5) or 0.5,
        tool_call=tc,
        response_hint=obj.get('response_hint', '')
    )
"@

# skills/__init__.py
Write-File "$root\skills\__init__.py" @"
from .registry import SKILLS, register
# auto-import core skills
from . import core_time, core_memory  # noqa: F401
"@

# skills/registry.py
Write-File "$root\skills\registry.py" @"
from typing import Callable, Dict, Any

_SKILLS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

def register(name: str):
    def deco(fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        _SKILLS[name] = fn
        return fn
    return deco

def get(name: str):
    return _SKILLS.get(name)

SKILLS = _SKILLS
"@

# skills/core_time.py
Write-File "$root\skills\core_time.py" @"
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
"@

# skills/core_memory.py
Write-File "$root\skills\core_memory.py" @"
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
"@

# memory/__init__.py
Write-File "$root\memory\__init__.py" @"
# memory package (profile/episodic/retriever)
"@

# memory/profile_store.py
Write-File "$root\memory\profile_store.py" @"
# Optional: higher-level profile helpers (wrap firebase_db)
"@

# memory/episodic_store.py
Write-File "$root\memory\episodic_store.py" @"
# Optional: store short turn summaries + embeddings (FAISS/sqlite)
"@

# memory/retriever.py
Write-File "$root\memory\retriever.py" @"
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
"@

Write-Host " $root package created."
Write-Host "Next: ensure your PYTHONPATH includes the project root so 'import $root' works."
