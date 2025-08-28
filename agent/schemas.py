from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List


class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    intent: str = "respond"
    confidence: float = 0.5
    tool_call: Optional[ToolCall] = None
    response_hint: Optional[str] = None  # 🔧 Fix: allow None safely

    @validator("confidence")
    def _clamp(cls, v):
        return max(0.0, min(1.0, float(v)))


class Grounding(BaseModel):
    now_human: str
    tz: str
    assistant_name: Optional[str] = None
    user_name: Optional[str] = None
    facts: Dict[str, str] = Field(default_factory=dict)
    reminders: List[Dict[str, Any]] = Field(default_factory=list)
    episodes: List[str] = Field(default_factory=list)


class Observation(BaseModel):
    tool: Optional[str] = None
    result: Dict[str, Any] = Field(default_factory=dict)
