import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.schemas.common import BaseSchema

class OrganizationRead(BaseSchema):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime

class BusinessRead(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    category: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

class BusinessLocationRead(BaseSchema):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    address: Optional[str] = None
    timezone: str
    status: str
    created_at: datetime
    updated_at: datetime

class SupervisorProfileRead(BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str
    status: str
    created_at: datetime

class OrganizationMembershipRead(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    supervisor_id: uuid.UUID
    role: str
    status: str
    organization: Optional[OrganizationRead] = None
