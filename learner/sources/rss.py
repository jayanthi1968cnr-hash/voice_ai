from __future__ import annotations
from typing import List
import xml.etree.ElementTree as ET
import requests

def fetch_feed_urls(feed_url: str) -> List[str]:
    """Minimal RSS/Atom fetcher: returns entry links (best-effort)."""
    urls: List[str] = []
    try:
        r = requests.get(feed_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        root = ET.fromstring(r.text)

        # RSS: <item><link>...</link>
        for item in root.findall(".//item"):
            link = item.findtext("link")
            if link:
                urls.append(link.strip())

        # Atom: <entry><link rel='alternate' href='...'/>
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
                href = link.attrib.get("href")
                rel = link.attrib.get("rel", "alternate")
                if href and rel == "alternate":
                    urls.append(href.strip())
    except Exception:
        pass
    return urls
