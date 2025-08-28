from __future__ import annotations
import re, os
from typing import Literal

from llm import ask_llm_full
from config import cfg

# Optional heavier model name via env; fallback to cfg.GROQ_MODEL
HEAVY_MODEL = os.getenv("GROQ_MODEL_HEAVY", "llama-3.1-70b-versatile")

def pick_style(query: str) -> dict:
    t = (query or "").lower()
    # simple heuristics
    if len(t) > 250 or re.search(r"\bwhy|how|design|explain|plan|strategy\b", t):
        return {"model": HEAVY_MODEL, "temperature": 0.5}
    return {"model": cfg.GROQ_MODEL, "temperature": cfg.LLM_TEMPERATURE}

def call_llm_with_style(prompt: str, style: dict) -> str:
    # Your ask_llm_full uses cfg.* internally; keep a single entry for now.
    # If you later add per-call model selection, route here.
    out = ask_llm_full(prompt) or ""
    return out.split("assistant\n",1)[-1].strip() if "assistant\n" in out else out.strip()
