# core/redact_pdf.py

from __future__ import annotations

from typing import List, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None

from .models import Span
from .policy import load_policy, Policy
from .detect_regex import find_regex_spans
from .detect_ner import ner_spans
from .resolve import merge_spans


# ---------------------------------------------------------------------
# Low-level helper (your original)
# ---------------------------------------------------------------------
def redact_pdf_in_place(
    input_path: str,
    output_path: str,
    spans_per_page: List[List[Tuple[Span, Tuple[float, float, float, float]]]],
) -> None:
    """
    Redact a PDF by drawing black rectangles and applying redactions.

    NOTE: This helper assumes you already mapped text spans to PDF coordinates.
    That mapping step (OCR + layout) is not implemented here.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF redaction")

    doc = fitz.open(input_path)

    for page_index, entries in enumerate(spans_per_page):
        if page_index >= len(doc):
            break
        page = doc[page_index]
        for _span, bbox in entries:
            rect = fitz.Rect(*bbox)
            page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    doc.save(output_path, deflate=True, garbage=4)
    doc.close()


# ---------------------------------------------------------------------
# Higher-level helper: bytes in → bytes out, auto-detect PII per page
# ---------------------------------------------------------------------
def _collect_spans(text: str, policy: Policy) -> List[Span]:
    """Collect regex + NER spans on a piece of text."""
    spans: List[Span] = []
    spans += find_regex_spans(text, policy)
    spans = merge_spans(spans)
    ners = ner_spans(text, policy)
    spans = merge_spans(spans, ners)
    return spans


def redact_pdf_bytes(
    data: bytes,
    policy_path: str = "configs/policy.yaml",
    mode: str = "blackout",
) -> bytes:
    """
    Visually redact a PDF in-memory using blackout/whiteout rectangles.

    - Keeps layout and formatting.
    - Works for text-based PDFs (not scanned image-only PDFs).
    - Uses the same policy / regex / NER you use for text redaction.

    mode:
      - "blackout": black rectangles over PII
      - "whiteout": white rectangles over PII

    Returns:
      redacted PDF as bytes.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF redaction")

    if mode not in ("blackout", "whiteout"):
        # Non-visual modes don't make sense here; default to blackout.
        mode = "blackout"

    policy = load_policy(policy_path)
    doc = fitz.open(stream=data, filetype="pdf")

    fill_color = (0, 0, 0) if mode == "blackout" else (1, 1, 1)

    for page in doc:
        page_text = page.get_text("text")
        if not page_text or not page_text.strip():
            # Likely an image-only / scanned page; nothing to redact
            continue

        spans = _collect_spans(page_text, policy)

        for span in spans:
            original = page_text[span.start:span.end]
            if not original.strip():
                continue

            # Search for this substring on the page and redact all matches
            rects = page.search_for(original)
            for rect in rects:
                page.add_redact_annot(rect, fill=fill_color)

        # Apply all redactions on this page
        page.apply_redactions()

    out_bytes = doc.tobytes()
    doc.close()
    return out_bytes
