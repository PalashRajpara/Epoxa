"""
Appointment service implementing business rules, slot validation, and code generation.
Conforms strictly to Decision D3 (Asia/Kolkata, Mon-Sat 09:00-18:00) and D4 (30-min slots).
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from epoxa_core.exceptions import ConflictError, EntityNotFoundError, ValidationError
from epoxa_core.models.entities import Appointment
from epoxa_core.uow import UnitOfWork

# Unambiguous alphabet excluding 0, O, 1, I, L to prevent transcription and spoken ambiguity
UNAMBIGUOUS_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_confirmation_code(length: int = 7) -> str:
    """Generates an unambiguous uppercase alphanumeric confirmation code."""
    return "".join(secrets.choice(UNAMBIGUOUS_ALPHABET) for _ in range(length))


class AppointmentService:
    """Handles appointment booking validation, business hour checks, and persistence."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def validate_slot_within_business_hours(
        self,
        scheduled_at: datetime,
        tz_name: str = "Asia/Kolkata",
        start_hour: int = 9,
        end_hour: int = 18,
        allowed_weekdays: Optional[List[int]] = None,
    ) -> None:
        """
        Validates that the appointment:
        1. Is not in the past
        2. Falls on a business day (Mon-Sat, where Monday is 0, Sunday is 6)
        3. Falls within operating hours (09:00 - 18:00 in tenant timezone)
        """
        now_utc = datetime.now(timezone.utc)
        if scheduled_at <= now_utc:
            raise ValidationError("Appointments cannot be scheduled in the past.")

        allowed_days = allowed_weekdays if allowed_weekdays is not None else [0, 1, 2, 3, 4, 5]
        local_time = scheduled_at.astimezone(ZoneInfo(tz_name))

        if local_time.weekday() not in allowed_days:
            raise ValidationError(
                f"Appointments can only be scheduled Monday through Saturday in timezone '{tz_name}'."
            )

        if local_time.hour < start_hour or (local_time.hour >= end_hour):
            raise ValidationError(
                f"Appointments must be scheduled within business hours ({start_hour:02d}:00 to {end_hour:02d}:00 {tz_name})."
            )

    async def book_appointment(
        self,
        organization_id: uuid.UUID,
        customer_id: uuid.UUID,
        scheduled_at: datetime,
        session_id: Optional[uuid.UUID] = None,
        duration_minutes: int = 30,
        notes: Optional[str] = None,
    ) -> Appointment:
        """Books a verified 30-minute appointment slot."""
        # 1. Fetch organization settings for business hours
        org = await self.uow.organizations.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError("Organization", organization_id)

        settings_dict = org.settings or {}
        b_hours = settings_dict.get("business_hours", {})
        tz_name = org.timezone or "Asia/Kolkata"

        self.validate_slot_within_business_hours(
            scheduled_at=scheduled_at,
            tz_name=tz_name,
            start_hour=b_hours.get("start", 9),
            end_hour=b_hours.get("end", 18),
        )

        # 2. Check for slot conflict (D4)
        is_free = await self.uow.appointments.is_slot_available(organization_id, scheduled_at)
        if not is_free:
            raise ConflictError(
                f"The slot at {scheduled_at.isoformat()} is already booked. Please choose an alternative time."
            )

        # 3. Generate collision-resistant confirmation code
        confirmation_code = ""
        for _ in range(5):  # Max 5 attempts on collision
            candidate = f"APT-{generate_confirmation_code(6)}"
            existing = await self.uow.appointments.get_by_code(organization_id, candidate)
            if not existing:
                confirmation_code = candidate
                break

        if not confirmation_code:
            confirmation_code = f"APT-{uuid.uuid4().hex[:8].upper()}"

        # 4. Create appointment entity
        appointment = Appointment(
            organization_id=organization_id,
            customer_id=customer_id,
            session_id=session_id,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            timezone=tz_name,
            confirmation_code=confirmation_code,
            status="confirmed",
            notes=notes,
        )
        self.uow.appointments.add(appointment)
        await self.uow.commit()
        return appointment

    async def suggest_alternative_slots(
        self,
        organization_id: uuid.UUID,
        target_time: datetime,
        count: int = 3,
    ) -> List[datetime]:
        """Suggests the next available free 30-minute slots if a requested time is busy."""
        alternatives: List[datetime] = []
        candidate = target_time
        org = await self.uow.organizations.get_by_id(organization_id)
        tz_name = org.timezone if org else "Asia/Kolkata"

        for _ in range(12):  # Scan next 6 hours
            candidate += timedelta(minutes=30)
            try:
                self.validate_slot_within_business_hours(candidate, tz_name=tz_name)
            except ValidationError:
                continue

            if await self.uow.appointments.is_slot_available(organization_id, candidate):
                alternatives.append(candidate)
                if len(alternatives) >= count:
                    break

        return alternatives

    async def cancel_appointment(
        self,
        organization_id: uuid.UUID,
        confirmation_code: str,
        reason: str,
    ) -> Appointment:
        """Cancels an existing appointment."""
        appointment = await self.uow.appointments.get_by_code(organization_id, confirmation_code)
        if not appointment:
            raise EntityNotFoundError("Appointment", confirmation_code)

        if appointment.status == "cancelled":
            return appointment

        appointment.status = "cancelled"
        appointment.cancelled_at = datetime.now(timezone.utc)
        appointment.cancellation_reason = reason
        await self.uow.commit()
        return appointment
