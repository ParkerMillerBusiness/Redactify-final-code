# core/pipeline.py

from __future__ import annotations

from typing import Tuple, List, Iterable, Optional

from .models import Span
from .policy import load_policy, Policy
from .detect_regex import find_regex_spans
from .detect_ner import ner_spans
from .resolve import merge_spans
from .transform import apply_actions


def _collect_spans(text: str, policy: Policy) -> List[Span]:
    spans: List[Span] = []

    # 1) Deterministic PII (regex)
    spans += find_regex_spans(text, policy)
    spans = merge_spans(spans)

    # 2) Unstructured PII (spaCy NER)
    ners = ner_spans(text, policy)
    spans = merge_spans(spans, ners)

    return spans


def redact_text(
    text: str,
    policy_path: str = "configs/policy.yaml",
    mode: str = "placeholder",
    allowed_entities: Optional[Iterable[str]] = None,
) -> Tuple[str, List[Span]]:
    """
    Redact text using the given policy and mode.

    allowed_entities:
      - If None: use all entities defined in policy.
      - If iterable: only spans whose ent is in this set will be redacted.
    """
    policy = load_policy(policy_path)
    spans = _collect_spans(text, policy)

    if allowed_entities is not None:
        allowed_set = set(allowed_entities)
        spans = [s for s in spans if s.ent in allowed_set]

    redacted = apply_actions(text, spans, policy, mode)
    return redacted, spans
