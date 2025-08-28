from __future__ import annotations
from typing import List
import time

try:
    from firebase_db import db, COLL, DOC  # reuse your Firestore client if present
except Exception:
    db, COLL, DOC = None, "users", "shiva"

def upsert_page(url: str, title: str, site: str, summary: str):
    """Store a compact page summary document in Firestore (merge-upsert)."""
    if not db:
        print(f"[store] (no DB) page: {url}")
        return
    ref = db.collection(COLL).document(DOC).collection("knowledge").document("pages")
    ref.set({
        "data": {
            url: {
                "title": title,
                "site": site,
                "summary": summary,
                "updated_at": time.time()
            }
        }
    }, merge=True)

def store_chunks(url: str, title: str, site: str, chunks: List[str], vecs):
    """Append chunks (and optional vectors) into knowledge/chunks (capped)."""
    if not db:
        print(f"[store] (no DB) chunks: {len(chunks)} from {url}")
        return
    vectors = vecs.tolist() if hasattr(vecs, "tolist") else (vecs or [])
    items = []
    for i, txt in enumerate(chunks):
        v = vectors[i] if i < len(vectors) else []
        items.append({"url": url, "title": title, "site": site, "text": txt, "vector": v, "ts": time.time()})
    ref = db.collection(COLL).document(DOC).collection("knowledge").document("chunks")
    snap = ref.get()
    cur = (snap.to_dict() or {}).get("data", [])
    cur.extend(items)
    if len(cur) > 20000:
        cur = cur[-20000:]
    ref.set({"data": cur}, merge=True)
