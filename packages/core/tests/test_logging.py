"""
Unit tests for structured logging and PII redaction.
"""

from epoxa_core.logging import mask_pii_string, pii_masking_processor


def test_mask_email() -> None:
    text = "Contact support at customer.test@example.com for questions."
    masked = mask_pii_string(text)
    assert "customer.test@example.com" not in masked
    assert "@example.com" in masked
    assert "***" in masked


def test_mask_phone_number() -> None:
    text = "Caller said their phone is +919876543210."
    masked = mask_pii_string(text)
    assert "+919876543210" not in masked
    assert "***" in masked


def test_mask_jwt() -> None:
    fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignatureValue123"
    text = f"Bearer {fake_jwt}"
    masked = mask_pii_string(text)
    assert fake_jwt not in masked
    assert "[REDACTED_JWT]" in masked


def test_pii_processor_masks_sensitive_event_keys() -> None:
    event_dict = {
        "event": "customer_lookup",
        "phone": "+919876543210",
        "email": "user@test.com",
        "api_key": "supersecretkey123",
    }
    processed = pii_masking_processor(None, "info", event_dict)
    assert "+919876543210" not in processed["phone"]
    assert "user@test.com" not in processed["email"]
    assert processed["api_key"] == "[REDACTED]"
