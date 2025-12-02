# core/resolve.py

from __future__ import annotations

from typing import List
from core.models import Span


def merge_spans(primary: List[Span], extra: List[Span] | None = None) -> List[Span]:
    """
    Merge two span lists and resolve overlaps by:
    - preferring higher confidence
    - breaking ties by preferring longer spans
    """

    spans = list(primary)
    if extra:
        spans.extend(extra)

    if not spans:
        return []

    spans.sort(key=lambda s: (s.start, -s.end))

    result: List[Span] = []
    for span in spans:
        if not result:
            result.append(span)
            continue

        last = result[-1]
        if not last.overlaps(span):
            result.append(span)
            continue

        # On overlap, choose better span
        if span.conf > last.conf + 1e-6:
            result[-1] = span
        elif abs(span.conf - last.conf) <= 1e-6 and span.length() > last.length():
            result[-1] = span
        # else keep last

    return result
