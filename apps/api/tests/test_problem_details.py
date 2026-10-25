"""Test suite for RFC 7807 Problem Details serialization."""

from epoxa_api.schemas import ProblemDetails

def test_problem_details_structure() -> None:
    p = ProblemDetails(
        type="https://epoxa.ai/errors/slot_unavailable",
        title="Appointment Slot Unavailable",
        status=409,
        detail="The slot at 2:00 PM is already booked.",
        instance="/api/v1/appointments",
        request_id="req-12345",
    )
    data = p.model_dump()
    assert data["status"] == 409
    assert data["title"] == "Appointment Slot Unavailable"
    assert data["request_id"] == "req-12345"
    assert "detail" in data
