from __future__ import annotations
from typing import List, Tuple, Dict
import math

# Minimal vector ops (works even without numpy)
def dot(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b)); s = 0.0
    for i in range(n): s += a[i]*b[i]
    return s

def norm(a: list[float]) -> float:
    return math.sqrt(sum(x*x for x in a))

def cosine(a: list[float], b: list[float]) -> float:
    na, nb = norm(a), norm(b)
    if na == 0 or nb == 0: return 0.0
    return dot(a, b) / (na*nb)

# Fetch chunks with vectors from Firestore knowledge/chunks
try:
    from firebase_db import db, COLL, DOC
except Exception:
    db, COLL, DOC = None, "users", "shiva"

def load_all_chunks() -> list[dict]:
    if not db: return []
    ref = db.collection(COLL).document(DOC).collection("knowledge").document("chunks").get()
    return (ref.to_dict() or {}).get("data", [])

def topk_by_cosine(query_vec: list[float], items: list[dict], k: int = 5) -> list[dict]:
    scored = []
    for it in items:
        v = it.get("vector") or []
        if not v: continue
        scored.append((cosine(query_vec, v), it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:k]]
