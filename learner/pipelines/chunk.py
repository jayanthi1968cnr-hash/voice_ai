from __future__ import annotations
from typing import List
import re

def split_chunks(text: str, max_chars: int = 1000, min_chars: int = 300) -> List[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    out: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + max_chars)
        chunk = text[start:end]
        if len(chunk) < min_chars and end < n:
            nxt = text.find(".", end)
            if nxt != -1:
                end = min(nxt + 1, n)
                chunk = text[start:end]
        out.append(chunk.strip())
        start = end
    return [c for c in out if c]
