"""
Customer management API endpoints (Supervisor / Admin authenticated).
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from epoxa_api.auth.dependencies import AuthenticatedContext, require_role
from epoxa_api.schemas import (
    CustomerCreateRequest,
    CustomerListResponse,
    CustomerResponse,
)
from epoxa_core.exceptions import EntityNotFoundError
from epoxa_core.services.customer_service import CustomerService
from epoxa_core.uow import UnitOfWork

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> CustomerListResponse:
    """Lists verified customer profiles within the supervisor's organization."""
    async with UnitOfWork() as uow:
        service = CustomerService(uow)
        customers = await service.list_customers(ctx.organization_id, limit=limit, offset=offset)
        return CustomerListResponse(
            customers=[
                CustomerResponse(
                    id=c.id,
                    name=c.name,
                    phone_e164=c.phone_e164,
                    email=c.email,
                    tier=c.tier,
                    created_at=c.created_at,
                )
                for c in customers
            ],
            total=len(customers),
            limit=limit,
            offset=offset,
        )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> CustomerResponse:
    """Retrieves a specific customer profile."""
    async with UnitOfWork() as uow:
        customer = await uow.customers.get_by_id(customer_id)
        if not customer or customer.organization_id != ctx.organization_id:
            raise EntityNotFoundError("Customer", customer_id)

        return CustomerResponse(
            id=customer.id,
            name=customer.name,
            phone_e164=customer.phone_e164,
            email=customer.email,
            tier=customer.tier,
            created_at=customer.created_at,
        )


@router.post("", response_model=CustomerResponse)
async def create_customer(
    body: CustomerCreateRequest,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> CustomerResponse:
    """Registers a new customer profile manually."""
    async with UnitOfWork() as uow:
        service = CustomerService(uow)
        customer = await service.register_customer(
            organization_id=ctx.organization_id,
            name=body.name,
            phone=body.phone,
            email=body.email,
            tier=body.tier,
            metadata=body.metadata,
        )
        return CustomerResponse(
            id=customer.id,
            name=customer.name,
            phone_e164=customer.phone_e164,
            email=customer.email,
            tier=customer.tier,
            created_at=customer.created_at,
        )


@router.post("/{customer_id}/anonymize", response_model=CustomerResponse)
async def anonymize_customer(
    customer_id: uuid.UUID,
    ctx: AuthenticatedContext = Depends(require_role("admin")),
) -> CustomerResponse:
    """GDPR/Privacy right-to-be-forgotten customer anonymization (Admin only)."""
    async with UnitOfWork() as uow:
        service = CustomerService(uow)
        anonymized = await service.anonymize_customer(
            organization_id=ctx.organization_id,
            customer_id=customer_id,
        )
        return CustomerResponse(
            id=anonymized.id,
            name=anonymized.name,
            phone_e164=anonymized.phone_e164,
            email=anonymized.email,
            tier=anonymized.tier,
            created_at=anonymized.created_at,
        )
