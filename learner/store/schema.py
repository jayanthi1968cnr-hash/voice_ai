from __future__ import annotations
from dataclasses import dataclass
from typing import List

@dataclass
class ChunkRecord:
    url: str
    title: str
    site: str
    text: str
    vector: list   # list[float]
