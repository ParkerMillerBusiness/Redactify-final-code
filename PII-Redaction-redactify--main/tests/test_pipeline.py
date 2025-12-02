# tests/test_pipeline.py

from core.pipeline import redact_text


def test_redact_basic():
    text = "John Doe's email is john.doe@example.com and phone is (555) 123-4567."
    redacted, spans = redact_text(text, "configs/policy.yaml", mode="placeholder")

    ents = {s.ent for s in spans}
    assert "EMAIL" in ents
    assert "PHONE" in ents

    assert "john.doe@example.com" not in redacted
    assert "(555) 123-4567" not in redacted

