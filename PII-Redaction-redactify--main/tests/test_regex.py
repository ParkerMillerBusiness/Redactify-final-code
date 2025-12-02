# tests/test_regex.py

from core.policy import load_policy
from core.detect_regex import find_regex_spans


def test_email_detection():
    policy = load_policy("configs/policy.yaml")
    text = "Contact me at user@example.com please."
    spans = find_regex_spans(text, policy)
    emails = [s for s in spans if s.ent == "EMAIL"]
    assert len(emails) == 1
    assert text[emails[0].start:emails[0].end] == "user@example.com"
