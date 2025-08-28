# app/text_utils.py
from __future__ import annotations
import re
from html import unescape

# Common role labels we want to strip from logs/LLM output
_ROLE_WORDS = ("system", "assistant", "user", "tool", "developer", "function")

def strip_role_blocks(text: str) -> str:
    """
    Remove 'role' wrappers that some LLM outputs include, e.g.:
      ```assistant
      ...
      ```
    or lines that begin with 'assistant:', 'system:', etc.
    """
    if not text:
        return ""

    s = str(text)

    # 1) Remove fenced code blocks labeled with a role: ```assistant ... ```
    fenced = re.compile(
        r"```(?:\s*)(?:%s)\b.*?```" % "|".join(_ROLE_WORDS),
        flags=re.IGNORECASE | re.DOTALL,
    )
    s = fenced.sub("", s)

    # 2) Remove bare role headers/lines like "assistant" or "assistant:" on their own line
    line_role_only = re.compile(rf"(?mi)^\s*(?:{'|'.join(_ROLE_WORDS)})\s*$")
    s = line_role_only.sub("", s)

    line_role_colon = re.compile(rf"(?mi)^\s*(?:{'|'.join(_ROLE_WORDS)})\s*:\s*")
    s = line_role_colon.sub("", s)

    # 3) Collapse excessive blank lines and trim
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def tts_sanitize(text: str, max_chars: int = 1200) -> str:
    """
    Make text safe/nice for TTS:
      - strip role wrappers / code fences
      - unescape HTML entities
      - remove SSML-ish angle brackets/braces
      - collapse whitespace
      - hard-cap length on word boundary
    """
    if not text:
        return ""

    s = strip_role_blocks(text)
    s = unescape(s)
    s = s.replace("\r", "")
    # Avoid accidental SSML/control characters in TTS engines
    s = re.sub(r"[<>{}]", "", s)
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()

    if len(s) > max_chars:
        # Trim on a word boundary if possible
        cut = s[:max_chars]
        space = cut.rfind(" ")
        s = (cut[:space] if space > 50 else cut).rstrip() + "..."

    return s


def sanitize_for_log(text: str, max_len: int = 4000) -> str:
    """Safer string for log files."""
    s = strip_role_blocks(text or "")
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s


def collapse_ws(text: str) -> str:
    """Light whitespace collapse."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def clean_stt_text(text: str) -> str:
    """
    Clean speech-to-text (STT) output by removing filler words,
    fixing spacing, and normalizing the format.
    """
    if not text:
        return ""

    text = text.strip()

    # Remove filler words (adjust this list based on real-world data)
    text = re.sub(r"\b(um+|uh+|like|you know|hmm+|erm+|ah+)\b", "", text, flags=re.IGNORECASE)

    # Remove repeated spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()
