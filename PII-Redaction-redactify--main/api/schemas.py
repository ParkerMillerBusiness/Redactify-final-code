# api/schemas.py

from typing import List, Optional
from pydantic import BaseModel


class SpanSchema(BaseModel):
    start: int
    end: int
    ent: str
    conf: float
    source: str
    replacement: Optional[str] = None


class RedactRequest(BaseModel):
    text: str
    policy_name: str = "configs/policy.yaml"
    mode: str = "placeholder"  # or "mask"


class RedactResponse(BaseModel):
    redacted_text: str
    spans: List[SpanSchema]
