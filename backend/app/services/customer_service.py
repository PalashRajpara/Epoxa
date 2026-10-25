import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.customer_repo import customer_repo
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.core.exceptions import ResourceNotFoundError

class CustomerService:
    async def get_customer(self, db: AsyncSession, org_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
        customer = await customer_repo.get_by_id(db, customer_id=customer_id, org_id=org_id)
        if not customer:
            raise ResourceNotFoundError("Customer", customer_id)
        return customer

    async def list_customers(
        self, db: AsyncSession, org_id: uuid.UUID, page: int = 1, page_size: int = 20, search: Optional[str] = None
    ) -> Tuple[List[Customer], int]:
        return await customer_repo.list_customers(db, org_id=org_id, page=page, page_size=page_size, search=search)

    async def create_customer(self, db: AsyncSession, org_id: uuid.UUID, data: CustomerCreate) -> Customer:
        return await customer_repo.create(db, org_id=org_id, data=data)

    async def update_customer(
        self, db: AsyncSession, org_id: uuid.UUID, customer_id: uuid.UUID, data: CustomerUpdate
    ) -> Customer:
        cust = await self.get_customer(db, org_id=org_id, customer_id=customer_id)
        return await customer_repo.update(db, customer=cust, data=data)

customer_service = CustomerService()
