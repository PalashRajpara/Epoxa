import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.common import BaseSchema

class TicketCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    category: str = Field(default="general", pattern="^(general|technical|billing|escalation)$")
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    customer_id: Optional[uuid.UUID] = None
    call_session_id: Optional[uuid.UUID] = None
    business_id: Optional[uuid.UUID] = None

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_supervisor_id: Optional[uuid.UUID] = None

class TicketRead(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    business_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    call_session_id: Optional[uuid.UUID] = None
    assigned_supervisor_id: Optional[uuid.UUID] = None
    ticket_number: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class EscalationRequest(BaseModel):
    call_session_id: uuid.UUID
    reason: str

class EscalationRead(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    call_session_id: uuid.UUID
    support_ticket_id: Optional[uuid.UUID] = None
    reason: str
    state: str
    requested_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime

class TakeoverActionRequest(BaseModel):
    action: str = Field(..., pattern="^(takeover_started|handback_to_ai|call_ended)$")
    notes: Optional[str] = None

class TakeoverEventRead(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    call_session_id: uuid.UUID
    supervisor_id: uuid.UUID
    action: str
    notes: Optional[str] = None
    created_at: datetime
