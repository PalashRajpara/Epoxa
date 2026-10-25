"""
Unit tests for CustomerService and phone normalization.
"""

import pytest
from epoxa_core.exceptions import ValidationError
from epoxa_core.services.customer_service import normalize_to_e164


def test_normalize_valid_indian_number() -> None:
    # 10 digit Indian number without country code
    normalized = normalize_to_e164("9876543210", default_region="IN")
    assert normalized == "+919876543210"

    # Number with spaces and dashes
    normalized_spaced = normalize_to_e164("98765-43210", default_region="IN")
    assert normalized_spaced == "+919876543210"

    # With leading zero
    normalized_zero = normalize_to_e164("09876543210", default_region="IN")
    assert normalized_zero == "+919876543210"


def test_normalize_already_e164() -> None:
    normalized = normalize_to_e164("+919876543210", default_region="IN")
    assert normalized == "+919876543210"


def test_normalize_us_number() -> None:
    normalized = normalize_to_e164("4155552671", default_region="US")
    assert normalized == "+14155552671"


def test_normalize_invalid_number_raises_error() -> None:
    with pytest.raises(ValidationError):
        normalize_to_e164("12345", default_region="IN")

    with pytest.raises(ValidationError):
        normalize_to_e164("abcdefghij", default_region="IN")
