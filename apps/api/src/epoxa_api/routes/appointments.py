"""
Appointment scheduling API endpoints (Supervisor / Admin authenticated).
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from epoxa_api.auth.dependencies import AuthenticatedContext, require_role
from epoxa_api.schemas import (
    AppointmentCancelRequest,
    AppointmentCreateRequest,
    AppointmentListResponse,
    AppointmentResponse,
)
from epoxa_core.exceptions import EntityNotFoundError
from epoxa_core.services.appointment_service import AppointmentService
from epoxa_core.uow import UnitOfWork

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("", response_model=AppointmentListResponse)
async def list_appointments(
    status: Optional[str] = Query(None, description="Filter by status ('confirmed', 'cancelled', 'completed')"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> AppointmentListResponse:
    """Lists appointments for the tenant organization."""
    async with UnitOfWork() as uow:
        appointments = await uow.appointments.list_by_org(
            organization_id=ctx.organization_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return AppointmentListResponse(
            appointments=[
                AppointmentResponse(
                    id=a.id,
                    confirmation_code=a.confirmation_code,
                    customer_id=a.customer_id,
                    scheduled_at=a.scheduled_at,
                    duration_minutes=a.duration_minutes,
                    timezone=a.timezone,
                    status=a.status,
                    notes=a.notes,
                    created_at=a.created_at,
                )
                for a in appointments
            ],
            total=len(appointments),
            limit=limit,
            offset=offset,
        )


@router.get("/{confirmation_code}", response_model=AppointmentResponse)
async def get_appointment(
    confirmation_code: str,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> AppointmentResponse:
    """Retrieves an appointment by its human confirmation code."""
    async with UnitOfWork() as uow:
        appt = await uow.appointments.get_by_code(ctx.organization_id, confirmation_code)
        if not appt:
            raise EntityNotFoundError("Appointment", confirmation_code)

        return AppointmentResponse(
            id=appt.id,
            confirmation_code=appt.confirmation_code,
            customer_id=appt.customer_id,
            scheduled_at=appt.scheduled_at,
            duration_minutes=appt.duration_minutes,
            timezone=appt.timezone,
            status=appt.status,
            notes=appt.notes,
            created_at=appt.created_at,
        )


@router.post("", response_model=AppointmentResponse)
async def book_appointment(
    body: AppointmentCreateRequest,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> AppointmentResponse:
    """Books a verified appointment slot manually."""
    async with UnitOfWork() as uow:
        service = AppointmentService(uow)
        appt = await service.book_appointment(
            organization_id=ctx.organization_id,
            customer_id=body.customer_id,
            scheduled_at=body.scheduled_at,
            duration_minutes=body.duration_minutes,
            notes=body.notes,
        )
        return AppointmentResponse(
            id=appt.id,
            confirmation_code=appt.confirmation_code,
            customer_id=appt.customer_id,
            scheduled_at=appt.scheduled_at,
            duration_minutes=appt.duration_minutes,
            timezone=appt.timezone,
            status=appt.status,
            notes=appt.notes,
            created_at=appt.created_at,
        )


@router.post("/{confirmation_code}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    confirmation_code: str,
    body: AppointmentCancelRequest,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> AppointmentResponse:
    """Cancels an appointment."""
    async with UnitOfWork() as uow:
        service = AppointmentService(uow)
        appt = await service.cancel_appointment(
            organization_id=ctx.organization_id,
            confirmation_code=confirmation_code,
            reason=body.reason,
        )
        return AppointmentResponse(
            id=appt.id,
            confirmation_code=appt.confirmation_code,
            customer_id=appt.customer_id,
            scheduled_at=appt.scheduled_at,
            duration_minutes=appt.duration_minutes,
            timezone=appt.timezone,
            status=appt.status,
            notes=appt.notes,
            created_at=appt.created_at,
        )
