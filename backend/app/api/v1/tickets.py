import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_supervisor
from app.services.ticket_service import ticket_service
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketRead
from app.schemas.auth import SupervisorContext
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/tickets", tags=["Support Tickets"])

@router.get("", response_model=PaginatedResponse[TicketRead], summary="List support tickets")
async def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    items, total = await ticket_service.list_tickets(
        db, org_id=supervisor.organization_id, status=status, priority=priority, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{ticket_id}", response_model=TicketRead, summary="Get support ticket details")
async def get_ticket(
    ticket_id: uuid.UUID,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await ticket_service.get_ticket(db, org_id=supervisor.organization_id, ticket_id=ticket_id)

@router.post("", response_model=TicketRead, summary="Create support ticket")
async def create_ticket(
    req: TicketCreate,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await ticket_service.create_ticket(db, org_id=supervisor.organization_id, data=req)

@router.patch("/{ticket_id}", response_model=TicketRead, summary="Update support ticket")
async def update_ticket(
    ticket_id: uuid.UUID,
    req: TicketUpdate,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await ticket_service.update_ticket(
        db, org_id=supervisor.organization_id, ticket_id=ticket_id, data=req
    )
