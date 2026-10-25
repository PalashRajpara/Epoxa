import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.common import BaseSchema

class VoiceTokenRequest(BaseModel):
    customer_name: Optional[str] = Field(default=None, description="Optional caller name")
    customer_phone: Optional[str] = Field(default=None, description="Optional caller phone")
    business_id: Optional[uuid.UUID] = Field(default=None, description="Optional target business unit")

class VoiceTokenResponse(BaseModel):
    token: str
    room_name: str
    session_id: uuid.UUID
    livekit_url: str
    expires_in_seconds: int
    created_at: Optional[datetime] = None

class CallEventCreate(BaseModel):
    event_type: str
    actor: str = "customer"
    payload: Dict[str, Any] = {}

class CallEventRead(BaseSchema):
    id: uuid.UUID
    call_session_id: uuid.UUID
    event_type: str
    actor: str
    payload: Dict[str, Any]
    created_at: datetime

class TranscriptRead(BaseSchema):
    id: uuid.UUID
    call_session_id: uuid.UUID
    speaker: str
    content: Optional[str] = None
    is_purged: bool
    purged_at: Optional[datetime] = None
    created_at: datetime

class CallSummaryRead(BaseSchema):
    id: uuid.UUID
    call_session_id: uuid.UUID
    summary: str
    primary_intent: Optional[str] = None
    detected_sentiment: Optional[str] = None
    follow_up_required: bool
    created_at: datetime

class CallSessionRead(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    business_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    room_name: str
    status: str
    handoff_state: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    termination_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="custom_metadata")
    created_at: datetime
    updated_at: datetime
    summary: Optional[CallSummaryRead] = None
