"""
Unit tests for AppointmentService validation rules and confirmation code generation.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest

from epoxa_core.exceptions import ValidationError
from epoxa_core.services.appointment_service import (
    UNAMBIGUOUS_ALPHABET,
    AppointmentService,
    generate_confirmation_code,
)


def test_generate_confirmation_code_properties() -> None:
    code = generate_confirmation_code(7)
    assert len(code) == 7
    # Verify no ambiguous characters exist (0, O, 1, I, L)
    for ambiguous in ("0", "O", "1", "I", "L"):
        assert ambiguous not in code
    for char in code:
        assert char in UNAMBIGUOUS_ALPHABET


def test_validate_slot_past_date_raises_error() -> None:
    service = AppointmentService(uow=None)  # type: ignore
    past_date = datetime.now(timezone.utc) - timedelta(hours=2)

    with pytest.raises(ValidationError, match="past"):
        service.validate_slot_within_business_hours(past_date)


def test_validate_slot_sunday_raises_error() -> None:
    service = AppointmentService(uow=None)  # type: ignore
    # Find next Sunday
    tz = ZoneInfo("Asia/Kolkata")
    now_local = datetime.now(tz)
    days_until_sunday = (6 - now_local.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    next_sunday = (now_local + timedelta(days=days_until_sunday)).replace(hour=11, minute=0)
    next_sunday_utc = next_sunday.astimezone(timezone.utc)

    with pytest.raises(ValidationError, match="Monday through Saturday"):
        service.validate_slot_within_business_hours(next_sunday_utc)


def test_validate_slot_outside_business_hours_raises_error() -> None:
    service = AppointmentService(uow=None)  # type: ignore
    tz = ZoneInfo("Asia/Kolkata")
    now_local = datetime.now(tz)
    # Next Monday at 8 AM (business starts at 9 AM)
    days_until_monday = (0 - now_local.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    early_monday = (now_local + timedelta(days=days_until_monday)).replace(hour=8, minute=0)
    early_monday_utc = early_monday.astimezone(timezone.utc)

    with pytest.raises(ValidationError, match="within business hours"):
        service.validate_slot_within_business_hours(early_monday_utc)


def test_validate_slot_valid_business_hours_succeeds() -> None:
    service = AppointmentService(uow=None)  # type: ignore
    tz = ZoneInfo("Asia/Kolkata")
    now_local = datetime.now(tz)
    # Next Monday at 14:00 (2 PM)
    days_until_monday = (0 - now_local.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    valid_monday = (now_local + timedelta(days=days_until_monday)).replace(hour=14, minute=0)
    valid_monday_utc = valid_monday.astimezone(timezone.utc)

    # Should not raise any exception
    service.validate_slot_within_business_hours(valid_monday_utc)
