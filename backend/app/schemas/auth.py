import uuid
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.schemas.common import BaseSchema

class SupervisorContext(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    organization_id: uuid.UUID
    role: str

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: SupervisorContext

class SupervisorLoginRequest(BaseModel):
    email: EmailStr
    password: str

class DevLoginRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = "demo-password"
