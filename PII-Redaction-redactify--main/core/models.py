# core/models.py

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Span:
    start: int
    end: int
    ent: str
    conf: float
    source: str
    replacement: Optional[str] = None
    flags: Dict[str, bool] = field(default_factory=dict)

    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError(f"Invalid span [{self.start}, {self.end})")

    def overlaps(self, other: "Span") -> bool:
        return not (self.end <= other.start or other.end <= self.start)

    def length(self) -> int:
        return self.end - self.start
