from __future__ import annotations

BLOCK_PATTERNS = [
    r"(?i)\bmake\s+bomb\b",
    r"(?i)\bhack\s+.*password\b",
]

def is_blocked(text: str) -> bool:
    import re
    for p in BLOCK_PATTERNS:
        if re.search(p, text or ""):
            return True
    return False
