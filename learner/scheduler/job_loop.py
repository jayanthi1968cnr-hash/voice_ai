from __future__ import annotations
import os, time
from typing import List

from learner.sources.rss import fetch_feed_urls
from learner.sources.search import search_topics
from learner.pipelines.extract import fetch_and_extract
from learner.pipelines.chunk import split_chunks
from learner.pipelines.embed import embed_chunks
from learner.store.writer import upsert_page, store_chunks
from learner.policies.limits import cadence_minutes, max_pages_per_topic

CFG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")

def _read_list(yaml_path: str, key: str) -> List[str]:
    """
    Tiny YAML-ish list reader:
      key:
        - item a
        - item b
    Ignores other keys and comments.
    """
    items: List[str] = []
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            lines = [ln.rstrip() for ln in f.readlines()]
        in_key = False
        for ln in lines:
            if ln.strip().startswith("#"):
                continue
            if not in_key and ln.strip().startswith(f"{key}:"):
                in_key = True
                continue
            if in_key:
                if ln.strip().startswith("- "):
                    items.append(ln.strip()[2:].strip())
                elif ln.strip() == "" or ln.startswith(" "):
                    # still in block, skip
                    continue
                else:
                    break
    except Exception:
        pass
    return items

def run_loop():
    cad = cadence_minutes()
    pages_per_topic = max_pages_per_topic()

    feeds_path = os.path.join(CFG_DIR, "feeds.yaml")
    topics_path = os.path.join(CFG_DIR, "topics.yaml")
    default_feeds = ["https://hnrss.org/frontpage"]
    default_topics = ["AI news"]

    while True:
        try:
            feeds = _read_list(feeds_path, "feeds") or default_feeds
            topics = _read_list(topics_path, "topics") or default_topics

            urls: List[str] = []
            for feed in feeds:
                urls += fetch_feed_urls(feed)[:3]

            hits = search_topics(topics, count=pages_per_topic)
            urls += [h.get("url") for h in hits if h.get("url")]

            ingested = 0
            for url in dict.fromkeys([u for u in urls if u]).keys():
                title, site, text = fetch_and_extract(url)
                if not text:
                    continue
                upsert_page(url, title, site, text[:280])
                chunks = split_chunks(text)
                if not chunks:
                    continue
                vecs = embed_chunks(chunks)
                store_chunks(url, title, site, chunks, vecs)
                ingested += 1

            print(f"✅ Learner cycle complete. Ingested {ingested} page(s). Sleeping {cad} min…")
        except Exception as e:
            print(f"⚠️ Learner cycle error: {e}")
        time.sleep(cad * 60)
