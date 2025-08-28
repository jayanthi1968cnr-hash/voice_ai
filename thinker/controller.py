# thinker/controller.py
from thinker.state import TurnState
from thinker.policy import build_system_prompt
from thinker.reflect import light_reflect

from memory_catcher import catch_memory
from llm import ask_llm_full
from intent import classify_intent, maybe_empathy_reply, maybe_greeting_reply

try:
    from firebase_db import load_facts
    FIRE = True
except Exception:
    FIRE = False
    def load_facts(): return {}

def _maybe_local_answer(text: str) -> str | None:
    import re, datetime as dt
    t = (text or "").lower()
    if re.search(r"\b(time|date|today)\b", t):
        return f"The current time is {dt.datetime.now().strftime('%A, %d %B %Y, %I:%M %p')}."
    if t.startswith("what is my ") or t.startswith("who is my "):
        key = t.replace("what is my ", "").replace("who is my ", "").strip("? ")
        if FIRE:
            val = load_facts().get(key)
            if val: return f"Your {key} is {val}."
        return f"I don't have your {key} yet."
    return None

def think_and_act(state: TurnState, grounding: dict | None = None) -> str:
    local = _maybe_local_answer(state.user_text)
    if local:
        return local

    # light canned replies
    intent = classify_intent(state.user_text)
    canned = maybe_greeting_reply(state.user_text) or maybe_empathy_reply(state.user_text, intent)
    if canned:
        return canned

    gtxt = ""
    if grounding:
        gtxt = (
            "GROUND TRUTH (authoritative):\n"
            f"- Now: {grounding.get('now_human')} ({grounding.get('tz')})\n"
            f"- Assistant name: {grounding.get('assistant_name')}\n"
            f"- User name: {grounding.get('user_name')}\n"
            f"- Facts: {grounding.get('facts', {})}\n"
            f"- Reminders: {grounding.get('reminders', [])}\n"
        )
    sys_prompt = build_system_prompt(gtxt)
    raw = ask_llm_full(f"{sys_prompt}\n\nUser: {state.user_text}") or ""
    reply = raw.split("assistant\n", 1)[-1].strip() if "assistant\n" in raw else raw.strip()
    return light_reflect(reply)
