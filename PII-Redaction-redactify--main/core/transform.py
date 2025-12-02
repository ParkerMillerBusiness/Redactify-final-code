# core/transform.py

from __future__ import annotations

from typing import List, Dict
from core.models import Span
from core.policy import Policy


def apply_actions(text: str, spans: List[Span], policy: Policy, mode: str) -> str:
    """
    Apply mask/pseudonymization/redaction/etc. to text.

    mode:
      - "placeholder": use entity placeholders like PERSON_{n}
      - "mask": preserve some structure (e.g., j***e@domain.com)
      - "blackout": cover PII spans with █ characters
      - "whiteout": cover PII spans with spaces
    """
    pseudo_counters: Dict[str, int] = {}

    spans_sorted = sorted(spans, key=lambda s: s.start)
    out_parts = []
    cursor = 0

    for span in spans_sorted:
        if span.start > cursor:
            out_parts.append(text[cursor:span.start])

        ent = span.ent
        ep = policy.entity_policy(ent)
        action = policy.action_for(ent)
        original = text[span.start:span.end]
        replacement = original

        # --- Policy-driven action ---
        if action == "pseudonymize":
            ix = pseudo_counters.get(ent, 0) + 1
            pseudo_counters[ent] = ix
            placeholder = (ep.placeholder or f"{ent}_{{n}}").replace("{n}", str(ix))
            replacement = placeholder

        elif action == "redact":
            placeholder = ep.placeholder or f"[{ent}]"
            # support ADDRESS_{n} / DATE_{n} style placeholders
            if "{n}" in placeholder:
                ix = pseudo_counters.get(ent, 0) + 1
                pseudo_counters[ent] = ix
                placeholder = placeholder.replace("{n}", str(ix))
            replacement = placeholder

        elif action == "replace":
            placeholder = ep.placeholder or f"{ent}_VALUE"
            if "{n}" in placeholder:
                ix = pseudo_counters.get(ent, 0) + 1
                pseudo_counters[ent] = ix
                placeholder = placeholder.replace("{n}", str(ix))
            replacement = placeholder

        elif action == "mask":
            replacement = _mask_value(original, ep)

        elif action == "none":
            replacement = original

        # --- Global mode override: blackout / whiteout ---
        if mode == "blackout":
            # block characters ▉/█ for the entire span
            replacement = "█" * len(original)
        elif mode == "whiteout":
            # white space for the entire span (keeps length)
            replacement = " " * len(original)

        span.replacement = replacement
        out_parts.append(replacement)
        cursor = span.end

    if cursor < len(text):
        out_parts.append(text[cursor:])

    return "".join(out_parts)


def _mask_value(original: str, ep) -> str:
    ent = ep.id

    if ent == "EMAIL":
        return _mask_email(original, ep.mask_rules or {})

    if ent == "PHONE":
        rules = ep.mask_rules or {}
        mask_last = int(rules.get("mask_last", 4))
        digits = [c for c in original if c.isdigit()]
        if len(digits) <= mask_last:
            return "*" * len(original)
        keep = digits[-mask_last:]
        masked_digits = ["*"] * (len(digits) - mask_last) + keep

        out = []
        di = 0
        for ch in original:
            if ch.isdigit():
                out.append(masked_digits[di])
                di += 1
            else:
                out.append(ch)
        return "".join(out)

    out = []
    for ch in original:
        if ch.isalnum():
            out.append("*")
        else:
            out.append(ch)
    return "".join(out)


def _mask_email(email: str, rules: dict) -> str:
    keep_domain = bool(rules.get("keep_domain", True))
    keep_edge_chars = int(rules.get("keep_edge_chars", 1))

    if "@" not in email:
        return "*" * len(email)

    local, domain = email.split("@", 1)
    if len(local) <= 2 * keep_edge_chars:
        masked_local = "*" * len(local)
    else:
        mid_len = len(local) - 2 * keep_edge_chars
        masked_local = (
            local[:keep_edge_chars] + "*" * mid_len + local[-keep_edge_chars:]
        )

    if keep_domain:
        return f"{masked_local}@{domain}"
    return masked_local + "@***"
