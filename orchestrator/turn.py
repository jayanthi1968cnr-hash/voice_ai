# orchestrator/turn.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import re
from datetime import datetime

from config import cfg

# ---- Agent / Thinker / Memory glue ----
from memory_catcher import catch_memory                    # regex/quick parse
from agent.planner import plan_turn                        # high-level plan
from agent.affect import detect_affect                     # tone/emotion
from agent.skills.registry import get as get_skill         # tool registry
from agent.memory.retriever import build_grounding         # facts+now+reminders
from thinker.state import TurnState
from thinker.controller import think_and_act               # final LLM reply
from llm import llm_is_up                                  # health gate
from agent.tools import TOOL_FUNCTIONS

...

if plan.tool_call:
    tool_name = plan.tool_call.name
    args = plan.tool_call.args
    tool_fn = TOOL_FUNCTIONS.get(tool_name)
    if tool_fn:
        tool_result = tool_fn(args)
        reply = tool_result or plan.response_hint
    else:
        reply = f"Sorry, I don’t know how to handle the tool '{tool_name}'."

# ---- Firestore (optional) ----
if cfg.FIRESTORE_ENABLED:
    from firebase_db import (
        save_fact, load_facts, add_reminder, add_event, log_mood,
        delete_reminder_by_text, confirm_delete, get_timezone, get_reminders
    )
else:
    # stubs keep imports simple if Firestore is off
    def load_facts() -> Dict[str, Any]: return {}
    def get_reminders() -> List[Dict[str, Any]]: return []
    def confirm_delete(_: str) -> bool: return False
    def get_timezone() -> str: return "Asia/Kolkata"
    def save_fact(k: str, v: str): ...
    def add_reminder(text: str, when_iso: str): ...
    def delete_reminder_by_text(text: str): ...
    def add_event(title: str, date: str, emotion: str = ""): ...
    def log_mood(mood: str, note: str, ts: str): ...


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _now_human_and_iso() -> Tuple[str, str]:
    tz = "Asia/Kolkata"
    try:
        tz = get_timezone() or tz
    except Exception:
        pass

    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        now, tz = datetime.utcnow(), "UTC"

    human = now.strftime("%A, %d %B %Y, %I:%M %p")
    return f"{human} ({tz})", now.isoformat(timespec="seconds")


def _format_upcoming_reminders(limit: int = 5) -> List[str]:
    items = get_reminders() or []
    def _key(it): return (it.get("time") or it.get("whenISO") or "")
    items = sorted(items, key=_key)[:limit]
    out = []
    for it in items:
        msg = (it.get("message") or it.get("text") or "").strip()
        when = (it.get("time") or it.get("whenISO") or "").strip()
        out.append(f"- {msg} @ {when}" if when else f"- {msg}")
    return out


def _maybe_local_answer(text: str) -> Optional[str]:
    t = (text or "").lower().strip()

    # time/date quick path
    if re.search(r"\b(time|date|today|what(?:'s| is) the time)\b", t):
        human_now, _ = _now_human_and_iso()
        return f"The current time is {human_now}."

    # facts quick path
    if t.startswith("what is my ") or t.startswith("who is my "):
        key = t.replace("what is my ", "").replace("who is my ", "").strip("? ")
        facts = load_facts()
        val = facts.get(key) or facts.get(key.lower())
        if val:
            return f"Your {key} is {val}."
        return f"I don't have your {key} yet. Say 'remember that {key} is ...' to save it."
    return None


def _dispatch_tool(tool_call) -> Dict[str, Any]:
    """Run a registered tool; be tolerant to dict-like or attr-like objects."""
    if not tool_call:
        return {"ok": False, "error": "no tool"}
    name = getattr(tool_call, "name", None) or (isinstance(tool_call, dict) and tool_call.get("name"))
    args = getattr(tool_call, "args", None) or (isinstance(tool_call, dict) and tool_call.get("args")) or {}
    fn = get_skill(name)
    if not fn:
        return {"ok": False, "error": f"unknown tool '{name}'"}
    try:
        return fn(args or {})
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _apply_memory(parsed: Dict[str, Any]) -> List[str]:
    """Apply writes to Firestore based on catch_memory() output; return confirmations."""
    acks: List[str] = []
    # facts
    for key_raw, value in parsed.get("facts", []):
        key_norm = re.sub(r"\s+", "_", key_raw.strip().lower())
        try:
            save_fact(key_norm, value.strip())
            acks.append(f"{key_raw} = {value}")
        except Exception:
            pass
    # reminders
    for r in parsed.get("reminders", []):
        try:
            add_reminder(r["text"], r["when_iso"])
            acks.append(f"reminder '{r['text']}' @ {r['when_iso']}")
        except Exception:
            pass
    # events
    for ev in parsed.get("events", []):
        try:
            add_event(ev["title"], ev["date"], ev.get("emotion", ""))
            acks.append(f"event '{ev['title']}' on {ev['date']}")
        except Exception:
            pass
    # moods
    for m in parsed.get("moods", []):
        try:
            ts = datetime.now().replace(microsecond=0).isoformat()
            log_mood(m["mood"], m.get("note", ""), ts)
            acks.append(f"mood = {m['mood']}")
        except Exception:
            pass

    # explicit delete phrase (legacy)
    text = parsed.get("_raw", "")
    if text and confirm_delete(text.lower()):
        try:
            delete_reminder_by_text("take medicine")
            acks.append("deleted the 'take medicine' reminder")
        except Exception:
            pass

    return acks


# ---------------------------------------------------------
# Public: one function the app calls per turn
# ---------------------------------------------------------
@dataclass
class TurnResult:
    reply: str
    used_tool: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
    grounding: Optional[Dict[str, Any]] = None
    affect: Optional[Dict[str, Any]] = None
    confirmations: Optional[List[str]] = None


def handle_turn(user_text: str, history_ref: List[Dict[str, str]]) -> TurnResult:
    """
    The central brain for a single user turn.
    - Runs quick answers (time/facts)
    - Applies memory writes (facts/reminders/moods/events)
    - Plans tool usage; dispatches tools
    - Falls back to Thinker (LLM) with grounding
    Returns TurnResult (text + metadata). Does NOT speak or touch audio.
    """
    # 0) quick answers first
    quick = _maybe_local_answer(user_text)
    if quick:
        return TurnResult(reply=quick)

    # 1) detect affect and build grounding (facts/now/reminders/names)
    affect = detect_affect(user_text)
    grounding = build_grounding()

    # 2) memory catcher (regex) → if anything to write, do it & acknowledge
    parsed = catch_memory(user_text)
    parsed["_raw"] = user_text
    acks = _apply_memory(parsed)
    if acks:
        return TurnResult(reply="Got it! I’ll remember: " + "; ".join(acks) + ".", affect=affect, grounding=grounding, confirmations=acks)

    # 3) high-level plan (which may ask to run a tool)
    plan = plan_turn(user_text, grounding, affect)

    tool = getattr(plan, "tool_call", None) or (isinstance(plan, dict) and plan.get("tool_call"))
    if tool:
        result = _dispatch_tool(tool)

        # common confirmations
        name = getattr(tool, "name", None) or (isinstance(tool, dict) and tool.get("name"))
        if result.get("ok"):
            if name == "set_assistant_name":
                new_name = (getattr(tool, "args", None) or {}).get("name") or (isinstance(tool, dict) and (tool.get("args") or {}).get("name")) or "Assistant"
                return TurnResult(reply=f"Okay — from now on I’m {new_name}.", used_tool=name, tool_result=result, affect=affect, grounding=grounding)
            if name == "save_fact":
                args = getattr(tool, "args", None) or (isinstance(tool, dict) and tool.get("args")) or {}
                k = (args.get("key") or "").replace("_", " ")
                v = args.get("value") or ""
                return TurnResult(reply=f"Got it. I’ll remember your {k} is {v}.", used_tool=name, tool_result=result, affect=affect, grounding=grounding)
            if name == "add_reminder":
                args = getattr(tool, "args", None) or (isinstance(tool, dict) and tool.get("args")) or {}
                return TurnResult(reply=f"Reminder set: {args.get('text','')} at {args.get('when_iso','')}.", used_tool=name, tool_result=result, affect=affect, grounding=grounding)

        # tool failed or unhandled → continue to LLM
        if not result.get("ok"):
            pass

    # 4) if planner left a hint, we can answer quickly
    hint = getattr(plan, "response_hint", None) or (isinstance(plan, dict) and plan.get("response_hint"))
    if hint:
        return TurnResult(reply=hint, affect=affect, grounding=grounding)

    # 5) final: LLM “thinking” via Thinker
    if not llm_is_up(retries=1, wait_per_try=1):
        human_now, _ = _now_human_and_iso()
        return TurnResult(reply=f"My model brain is warming up. Meanwhile, the time is {human_now}.", affect=affect, grounding=grounding)

    state = TurnState(user_text=user_text, history=history_ref, affect=affect or {})
    llm_reply = think_and_act(state, grounding)
    return TurnResult(reply=llm_reply, affect=affect, grounding=grounding)
