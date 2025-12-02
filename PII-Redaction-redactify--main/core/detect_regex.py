# core/detect_regex.py

from __future__ import annotations

import regex as re
from typing import List
from core.models import Span
from core.policy import Policy
from core.validators import luhn_ok


EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"
)
SSN_RE = re.compile(
    r"\b(?!000|666|9\d{2})\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b"
)
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
)
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def find_regex_spans(text: str, policy: Policy) -> List[Span]:
    spans: List[Span] = []

    # Email
    if "EMAIL" in policy.entities:
        for m in EMAIL_RE.finditer(text):
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    ent="EMAIL",
                    conf=0.99,
                    source="regex",
                )
            )

    # Phone
    if "PHONE" in policy.entities:
        for m in PHONE_RE.finditer(text):
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    ent="PHONE",
                    conf=0.98,
                    source="regex",
                )
            )

    # SSN
    if "SSN_US" in policy.entities:
        for m in SSN_RE.finditer(text):
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    ent="SSN_US",
                    conf=0.99,
                    source="regex",
                )
            )

    # Date of birth (generic date pattern; policy can treat it as DOB)
    if "DOB" in policy.entities:
        for m in DATE_RE.finditer(text):
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    ent="DOB",
                    conf=0.7,
                    source="regex",
                )
            )

    # Credit card via Luhn
    if "CREDIT_CARD" in policy.entities:
        for m in CREDIT_CARD_RE.finditer(text):
            digits = re.sub(r"\D", "", m.group(0))
            if 13 <= len(digits) <= 19 and luhn_ok(digits):
                spans.append(
                    Span(
                        start=m.start(),
                        end=m.end(),
                        ent="CREDIT_CARD",
                        conf=0.99,
                        source="regex",
                    )
                )

    return spans
