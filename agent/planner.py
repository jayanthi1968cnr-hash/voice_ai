import json
from typing import Dict, Any, Optional

from .schemas import Plan, ToolCall
from .utils import extract_first_json
from llm import ask_llm_full  # ensure your app/ is on PYTHONPATH

SYSTEM = (
    'You are a planning controller for a voice assistant. '
    'Return JSON only. '
    'Schema: {"intent": str, "confidence": float, "tool_call": {"name": str, "args": object} | null, "response_hint": str} '
    'Valid tools: get_time, save_fact, add_reminder, set_assistant_name '
    'Rules: '
    '- If user says "your name is X"  set_assistant_name. '
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

    # Fix: Make sure response_hint is optional-safe
    hint = obj.get('response_hint')
    if hint is None or not isinstance(hint, str):
        hint = None  # Ensure it's not passed as empty string if invalid

    return Plan(
        intent=obj.get('intent', 'respond'),
        confidence=obj.get('confidence', 0.5) or 0.5,
        tool_call=tc,
        response_hint=hint
    )
