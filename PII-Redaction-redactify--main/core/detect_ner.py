from __future__ import annotations

from typing import List, Optional
from core.models import Span
from core.policy import Policy

import spacy

# Lazy-loaded spaCy model so import doesn't blow up if it's missing at install time
_NLP = None


def _get_nlp() -> "spacy.language.Language":
    global _NLP
    if _NLP is None:
        # Use the small English model; you can swap for a clinical model later
        _NLP = spacy.load("en_core_web_sm")
    return _NLP


# Map spaCy NER labels -> your internal entity IDs
LABEL_TO_ENTITY = {
    "PERSON": "PERSON_NAME",
    "GPE": "ADDRESS",   # countries, cities, states
    "LOC": "ADDRESS",   # general locations
    "FAC": "ADDRESS",   # facilities (can contain hospital names/locations)
    "ORG": None,        # you can map this to ORG_NAME later if you add it to policy
    "DATE": "DOB",      # heuristic: treat DATE as DOB; policy threshold can be high
}


def _map_label(label: str, policy: Policy) -> Optional[str]:
    ent = LABEL_TO_ENTITY.get(label)
    if ent is None:
        return None
    # Only keep entities that are actually configured in policy
    if ent not in policy.entities:
        return None
    return ent


def ner_spans(text: str, policy: Policy) -> List[Span]:
    """
    Use spaCy NER to detect unstructured PII:
    - PERSON -> PERSON_NAME
    - GPE/LOC/FAC -> ADDRESS
    - DATE -> DOB (heuristically)

    All processing is local; no external calls.
    """
    nlp = _get_nlp()
    doc = nlp(text)

    spans: List[Span] = []

    for ent in doc.ents:
        mapped = _map_label(ent.label_, policy)
        if mapped is None:
            continue

        # spaCy doesn't expose per-entity probs by default, so we give a
        # reasonable fixed confidence; you can tune this per-label if you want.
        base_conf = 0.85

        span = Span(
            start=ent.start_char,
            end=ent.end_char,
            ent=mapped,
            conf=base_conf,
            source="ner",
        )
        spans.append(span)

    return spans