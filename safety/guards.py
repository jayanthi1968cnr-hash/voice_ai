from __future__ import annotations

ALLOW_MUSIC_DOMAINS = {"music.amazon.", "music.youtube.", "open.spotify."}

def allow_browse(url: str) -> bool:
    if not url: return False
    lower = url.lower()
    return any(d in lower for d in ALLOW_MUSIC_DOMAINS)
