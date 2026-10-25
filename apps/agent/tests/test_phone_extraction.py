"""Test suite for spoken phone number extraction and normalization."""

import pytest
from epoxa_agent.nodes import normalize_spoken_digits

def test_spoken_digit_normalization() -> None:
    # "double nine" -> "99"
    assert "99" in normalize_spoken_digits("My number has double nine")
    # "triple zero" -> "000"
    assert "000" in normalize_spoken_digits("starts with triple zero")
    # "oh" for zero
    assert "9801" in normalize_spoken_digits("nine eight oh one")

def test_full_phone_number_cleaning() -> None:
    raw = "My phone is nine eight seven six five four three two one oh"
    cleaned = normalize_spoken_digits(raw)
    assert cleaned == "9876543210"
