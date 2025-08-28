from __future__ import annotations
from typing import List

# Hook up a real embedder later (e.g., sentence-transformers) and return numpy arrays.
def embed_chunks(chunks: List[str]):
    """Return a vector per chunk; placeholder returns empty vectors of same length."""
    return [[] for _ in chunks]
