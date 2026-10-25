import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_supervisor
from app.services.customer_service import customer_service
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerRead
from app.schemas.auth import SupervisorContext
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/customers", tags=["Customer Profiles"])

@router.get("", response_model=PaginatedResponse[CustomerRead], summary="List customers")
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    items, total = await customer_service.list_customers(
        db, org_id=supervisor.organization_id, page=page, page_size=page_size, search=search
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{customer_id}", response_model=CustomerRead, summary="Get customer profile")
async def get_customer(
    customer_id: uuid.UUID,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await customer_service.get_customer(db, org_id=supervisor.organization_id, customer_id=customer_id)

@router.post("", response_model=CustomerRead, summary="Create customer profile")
async def create_customer(
    req: CustomerCreate,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await customer_service.create_customer(db, org_id=supervisor.organization_id, data=req)

@router.patch("/{customer_id}", response_model=CustomerRead, summary="Update customer profile")
async def update_customer(
    customer_id: uuid.UUID,
    req: CustomerUpdate,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await customer_service.update_customer(
        db, org_id=supervisor.organization_id, customer_id=customer_id, data=req
    )
