# app/llm.py

import time
import json
import logging
import requests
from typing import Optional

from config import cfg

_last_llm_fail: float = 0.0


# ----------------------------
# Helpers
# ----------------------------
def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.GROQ_API_KEY}"
    }


def llm_is_up(retries: int = 3, wait_per_try: int = 10) -> bool:
    """Check if Groq LLM is available by sending a ping."""
    global _last_llm_fail

    cooldown = int(getattr(cfg, "LLM_HEALTHCHECK_SECONDS", 60))
    if (time.time() - _last_llm_fail) < cooldown:
        logging.debug("⏳ Skipping LLM check (within cooldown)")
        return False

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": cfg.GROQ_MODEL,
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0.0,
        "max_tokens": 5
    }

    headers = _headers()

    for attempt in range(1, retries + 1):
        try:
            print(f"⏳ Checking LLM backend... (try {attempt}/{retries})")
            r = requests.post(url, headers=headers, json=payload, timeout=(5, 10))
            if r.status_code == 200:
                print("✅ Groq LLM backend is awake.")
                return True
            else:
                logging.warning(f"⚠️ Healthcheck HTTP {r.status_code}: {r.text}")
        except Exception as e:
            logging.warning(f"❌ Healthcheck error: {e}")

        time.sleep(wait_per_try)

    _last_llm_fail = time.time()  # Only set if all attempts fail
    print("❌ LLM backend did not respond in time.")
    return False


# ----------------------------
# Main Ask Functions
# ----------------------------
def ask_llm_latency_gated(user_text: str, gate_seconds: float) -> Optional[str]:
    return _post_llm(user_text, gate_seconds)


def ask_llm_full(user_text: str) -> Optional[str]:
    timeout = float(getattr(cfg, "LLM_READ_TIMEOUT", 180.0))
    return _post_llm(user_text, timeout)


# ----------------------------
# Core Request Logic
# ----------------------------
def _post_llm(user_text: str, read_timeout: float) -> Optional[str]:
    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": cfg.GROQ_MODEL,
        "temperature": float(getattr(cfg, "LLM_TEMPERATURE", 0.3)),
        "max_tokens": int(getattr(cfg, "LLM_MAX_TOKENS", 512)),
        "messages": [
            {"role": "system", "content": cfg.SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]
    }

    try:
        r = requests.post(url, headers=_headers(), json=payload, timeout=(5, read_timeout))
        if r.status_code == 200:
            j = r.json()
            return j.get("choices", [{}])[0].get("message", {}).get("content", None)
        else:
            logging.warning(f"⚠️ Groq LLM error {r.status_code}: {r.text}")
    except Exception as e:
        logging.warning(f"❌ Exception during Groq LLM call: {e}")

    return None
