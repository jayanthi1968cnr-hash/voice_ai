from __future__ import annotations
from typing import List, Dict
from llm import ask_llm_full

SYSTEM = """You summarize dialogue. Keep it concise, preserve facts & user preferences."""

def summarize_history(history: List[Dict[str, str]], max_chars: int = 1200) -> str:
    if not history:
        return ""
    # Prepare compact transcript
    lines = []
    for m in history[-20:]:
        role = m.get("role", "user")[:9]
        content = (m.get("content") or "").strip().replace("\n", " ")
        lines.append(f"{role}: {content}")
    transcript = "\n".join(lines)[-3000:]
    prompt = f"{SYSTEM}\n\nTranscript:\n{transcript}\n\nReturn a short summary capturing key facts, preferences, tasks."
    out = ask_llm_full(prompt) or ""
    return out.split("assistant\n", 1)[-1].strip() if "assistant\n" in out else out.strip()
