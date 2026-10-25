import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.schemas.common import BaseSchema

class CustomerBase(BaseModel):
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    metadata: Dict[str, Any] = {}

class CustomerCreate(CustomerBase):
    business_id: Optional[uuid.UUID] = None

class CustomerUpdate(BaseModel):
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CustomerRead(CustomerBase, BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    business_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

class CustomerMatchQuery(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[str] = None
