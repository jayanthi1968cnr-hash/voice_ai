from __future__ import annotations
from typing import List, Dict
import os, requests

# Uses SerpAPI if SERPAPI_KEY present; otherwise returns [].
API_KEY = os.getenv("SERPAPI_KEY", "")

def web_search(query: str, count: int = 3) -> List[Dict]:
    if not API_KEY:
        return []
    url = "https://serpapi.com/search.json"
    params = {"engine": "google", "q": query, "num": count, "api_key": API_KEY}
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        out = []
        for item in (data.get("organic_results") or [])[:count]:
            out.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet")
            })
        return out
    except Exception:
        return []
