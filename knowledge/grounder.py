from __future__ import annotations
from typing import Dict, List

# Reuse your central embedder if available
try:
    from agent.memory.knowledge_store import embed_texts  # if you add one later
except Exception:
    embed_texts = None

from knowledge.index import load_all_chunks, topk_by_cosine

def retrieve(user_text: str, k: int = 5) -> Dict[str, List[str]]:
    chunks = load_all_chunks()
    if not chunks or embed_texts is None:
        return {"passages": []}
    vec = embed_texts([user_text])[0]
    hits = topk_by_cosine(vec, chunks, k=k)
    return {"passages": [h.get("text","") for h in hits]}
