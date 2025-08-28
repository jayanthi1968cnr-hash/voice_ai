# app/logging_utils.py
import os
import json
import logging
from datetime import datetime

from config import cfg
from text_utils import strip_role_blocks  # ensures we never log role blocks

# Logs folder relative to the app directory
LOGS_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)   # Ensure folder exists

TRANSCRIPT_PATTERN = "transcript_{date}.jsonl"
RAW_DEBUG_FILE = "raw_debug.jsonl"     # optional extra log for unsanitized payloads


def _today_file() -> str:
    return os.path.join(LOGS_DIR, TRANSCRIPT_PATTERN.format(date=datetime.now().strftime("%Y-%m-%d")))


def log_turn(role: str, text: str):
    """
    Write one conversation turn to the daily transcript JSONL.
    Text is sanitized to strip accidental role headers and code fences.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_text = strip_role_blocks(text or "")
    rec = {"ts": now, "role": role, "text": safe_text}

    try:
        with open(_today_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logging.error(f"Failed to write log: {e}")


def log_raw(role: str, payload):
    """
    (Optional) Append raw/unsanitized data to a separate debug JSONL file.
    Use only when debugging; avoids polluting the main transcript.
    """
    path = os.path.join(LOGS_DIR, RAW_DEBUG_FILE)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec = {"ts": now, "role": role, "raw": payload}
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logging.error(f"Failed to write raw debug log: {e}")


def save_context(turns: list[dict]):
    """
    Persist the last N conversation turns into context.json.
    """
    ctx_file = os.path.join(LOGS_DIR, "context.json")
    try:
        with open(ctx_file, "w", encoding="utf-8") as f:
            json.dump(turns[-(cfg.CONTEXT_TURNS * 2):], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Failed to save context: {e}")


def load_context() -> list[dict]:
    """
    Load previous conversation context from context.json.
    Returns [] if none or if parsing fails.
    """
    ctx_file = os.path.join(LOGS_DIR, "context.json")
    if os.path.exists(ctx_file):
        try:
            with open(ctx_file, "r", encoding="utf-8") as f:
                ctx = json.load(f)
                return ctx if isinstance(ctx, list) else []
        except Exception as e:
            logging.error(f"Failed to load context: {e}")
    return []


def should_sleep(text: str) -> bool:
    """
    Return True if the text contains a sleep word (pause command).
    Uses cfg.SLEEP_WORDS if present; falls back to defaults otherwise.
    """
    t = (text or "").lower().strip()
    sleep_words = getattr(cfg, "SLEEP_WORDS", ["sleep", "standby", "go to sleep"])
    return any(w in t for w in sleep_words)
