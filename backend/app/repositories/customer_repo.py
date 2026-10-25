import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate

class CustomerRepository:
    async def get_by_id(self, db: AsyncSession, customer_id: uuid.UUID, org_id: uuid.UUID) -> Optional[Customer]:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == org_id
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def find_match(
        self, db: AsyncSession, org_id: uuid.UUID, phone: Optional[str] = None, email: Optional[str] = None
    ) -> Optional[Customer]:
        """Cautiously finds existing customer within the organization."""
        if not phone and not email:
            return None

        conditions = []
        if phone:
            conditions.append(Customer.phone_number == phone.strip())
        if email:
            conditions.append(func.lower(Customer.email) == email.strip().lower())

        stmt = select(Customer).where(
            Customer.organization_id == org_id,
            or_(*conditions)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_customers(
        self, db: AsyncSession, org_id: uuid.UUID, page: int = 1, page_size: int = 20, search: Optional[str] = None
    ) -> Tuple[List[Customer], int]:
        query = select(Customer).where(Customer.organization_id == org_id)
        if search:
            s = f"%{search}%"
            query = query.where(
                or_(
                    Customer.display_name.ilike(s),
                    Customer.phone_number.ilike(s),
                    Customer.email.ilike(s),
                    Customer.company_name.ilike(s)
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        # Paginated items
        stmt = query.order_by(Customer.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await db.execute(stmt)).scalars().all())

        return items, total

    async def create(self, db: AsyncSession, org_id: uuid.UUID, data: CustomerCreate) -> Customer:
        customer = Customer(
            organization_id=org_id,
            business_id=data.business_id,
            display_name=data.display_name,
            phone_number=data.phone_number,
            email=data.email,
            company_name=data.company_name,
            metadata_=data.metadata
        )
        db.add(customer)
        await db.flush()
        return customer

    async def update(self, db: AsyncSession, customer: Customer, data: CustomerUpdate) -> Customer:
        if data.display_name is not None:
            customer.display_name = data.display_name
        if data.phone_number is not None:
            customer.phone_number = data.phone_number
        if data.email is not None:
            customer.email = data.email
        if data.company_name is not None:
            customer.company_name = data.company_name
        if data.metadata is not None:
            customer.metadata_ = {**customer.metadata_, **data.metadata}
        await db.flush()
        return customer

customer_repo = CustomerRepository()
