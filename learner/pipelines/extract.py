from __future__ import annotations
from typing import Tuple
import re, requests, urllib.parse

def _html_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.I|re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()

def fetch_and_extract(url: str) -> Tuple[str, str, str]:
    """
    Return (title, site, clean_text).
    Uses trafilatura if available; otherwise basic HTML strip fallback.
    """
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        html = r.text
    except Exception:
        return "", "", ""

    title = _html_title(html) or url
    site = urllib.parse.urlparse(url).netloc

    text = ""
    try:
        import trafilatura  # type: ignore
        text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    except Exception:
        text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I|re.S)
        text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I|re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    return title[:120], site, text
