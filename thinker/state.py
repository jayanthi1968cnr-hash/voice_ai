from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class TurnState:
    user_text: str
    history: List[Dict[str, str]] = field(default_factory=list)
    affect: Dict[str, Any] = field(default_factory=dict)
