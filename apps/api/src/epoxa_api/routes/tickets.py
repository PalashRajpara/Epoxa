"""
Support ticket management API endpoints (Supervisor authenticated).
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from epoxa_api.auth.dependencies import AuthenticatedContext, require_role
from epoxa_api.schemas import (
    TicketCreateRequest,
    TicketListResponse,
    TicketResponse,
    TicketUpdateRequest,
)
from epoxa_core.exceptions import EntityNotFoundError
from epoxa_core.services.ticket_service import TicketService
from epoxa_core.uow import UnitOfWork

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status ('open', 'in_progress', 'resolved', 'closed')"),
    category: Optional[str] = Query(None, description="Filter by category ('Complaint', 'Escalation', etc.)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> TicketListResponse:
    """Lists support tickets for the supervisor's organization."""
    async with UnitOfWork() as uow:
        service = TicketService(uow)
        tickets = await service.list_tickets(
            ctx.organization_id, status=status, category=category, limit=limit, offset=offset
        )
        return TicketListResponse(
            tickets=[
                TicketResponse(
                    id=t.id,
                    number=t.number,
                    category=t.category,
                    priority=t.priority,
                    description=t.description,
                    status=t.status,
                    assigned_to=t.assigned_to,
                    created_at=t.created_at,
                    resolved_at=t.resolved_at,
                )
                for t in tickets
            ],
            total=len(tickets),
            limit=limit,
            offset=offset,
        )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> TicketResponse:
    """Retrieves a specific support ticket by ID."""
    async with UnitOfWork() as uow:
        ticket = await uow.tickets.get_by_id(ticket_id)
        if not ticket or ticket.organization_id != ctx.organization_id:
            raise EntityNotFoundError("Ticket", ticket_id)

        return TicketResponse(
            id=ticket.id,
            number=ticket.number,
            category=ticket.category,
            priority=ticket.priority,
            description=ticket.description,
            status=ticket.status,
            assigned_to=ticket.assigned_to,
            created_at=ticket.created_at,
            resolved_at=ticket.resolved_at,
        )


@router.post("", response_model=TicketResponse)
async def create_ticket(
    body: TicketCreateRequest,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> TicketResponse:
    """Creates a new support ticket."""
    async with UnitOfWork() as uow:
        service = TicketService(uow)
        ticket = await service.create_ticket(
            organization_id=ctx.organization_id,
            category=body.category,
            priority=body.priority,
            description=body.description,
            customer_id=body.customer_id,
            session_id=body.session_id,
        )
        return TicketResponse(
            id=ticket.id,
            number=ticket.number,
            category=ticket.category,
            priority=ticket.priority,
            description=ticket.description,
            status=ticket.status,
            assigned_to=ticket.assigned_to,
            created_at=ticket.created_at,
            resolved_at=ticket.resolved_at,
        )


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: uuid.UUID,
    body: TicketUpdateRequest,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> TicketResponse:
    """Updates ticket status, priority, or assigned supervisor."""
    async with UnitOfWork() as uow:
        service = TicketService(uow)
        ticket = await service.update_ticket(
            organization_id=ctx.organization_id,
            ticket_id=ticket_id,
            status=body.status,
            priority=body.priority,
            assigned_to=body.assigned_to,
        )
        return TicketResponse(
            id=ticket.id,
            number=ticket.number,
            category=ticket.category,
            priority=ticket.priority,
            description=ticket.description,
            status=ticket.status,
            assigned_to=ticket.assigned_to,
            created_at=ticket.created_at,
            resolved_at=ticket.resolved_at,
        )
