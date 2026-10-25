"""
Strict Pydantic v2 schemas for Epoxa REST API endpoints.
All request models use extra='forbid' to reject unexpected properties.
Includes RFC 7807 Problem Details error envelope.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =============================================================================
# RFC 7807 PROBLEM DETAILS ERROR ENVELOPE
# =============================================================================

class ProblemDetails(BaseModel):
    """RFC 7807 compliant error format returned by all failed API responses."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(
        default="https://epoxa.ai/errors/internal",
        description="URI reference identifying the problem type",
    )
    title: str = Field(..., description="Short, human-readable summary of problem")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation of occurrence")
    instance: Optional[str] = Field(default=None, description="URI reference identifying occurrence")
    request_id: Optional[str] = Field(default=None, description="Distributed correlation ID")
    code: Optional[str] = Field(default=None, description="Domain error code string")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional structured debugging attributes")


# =============================================================================
# CALL SESSION SCHEMAS
# =============================================================================

class CallStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant_name: str = Field(default="Caller", min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=25)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CallStartResponse(BaseModel):
    session_id: str
    room_name: str
    token: str
    livekit_url: str
    identity: str


class CallTakeoverResponse(BaseModel):
    token: str
    identity: str
    room_name: str
    handoff_state: str


class TranscriptTurnResponse(BaseModel):
    id: int
    session_id: uuid.UUID
    sequence: int
    role: str
    speaker_identity: Optional[str]
    content: str
    spoken_at: datetime


class CallSessionResponse(BaseModel):
    id: uuid.UUID
    room_name: str
    participant_name: Optional[str]
    status: str
    handoff_state: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: int
    summary: Optional[str]
    end_reason: Optional[str]
    agent_version: str
    llm_model: str


class CallSessionListResponse(BaseModel):
    sessions: List[CallSessionResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# CUSTOMER SCHEMAS
# =============================================================================

class CustomerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=7, max_length=25)
    email: Optional[EmailStr] = None
    tier: str = Field(default="Standard", pattern="^(Basic|Standard|Premium|VIP)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone_e164: str
    email: Optional[str]
    tier: str
    created_at: datetime


class CustomerListResponse(BaseModel):
    customers: List[CustomerResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# APPOINTMENT SCHEMAS
# =============================================================================

class AppointmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=120)
    notes: Optional[str] = Field(default=None, max_length=1000)


class AppointmentCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=3, max_length=255)


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    confirmation_code: str
    customer_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    timezone: str
    status: str
    notes: Optional[str]
    created_at: datetime


class AppointmentListResponse(BaseModel):
    appointments: List[AppointmentResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# TICKET SCHEMAS
# =============================================================================

class TicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(default="General", pattern="^(Complaint|Escalation|Billing|General|Technical)$")
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    description: str = Field(..., min_length=5, max_length=2000)
    customer_id: Optional[uuid.UUID] = None
    session_id: Optional[uuid.UUID] = None


class TicketUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = Field(default=None, pattern="^(open|in_progress|resolved|closed)$")
    priority: Optional[str] = Field(default=None, pattern="^(low|normal|high|urgent)$")
    assigned_to: Optional[uuid.UUID] = None


class TicketResponse(BaseModel):
    id: uuid.UUID
    number: int
    category: str
    priority: str
    description: str
    status: str
    assigned_to: Optional[uuid.UUID]
    created_at: datetime
    resolved_at: Optional[datetime]


class TicketListResponse(BaseModel):
    tickets: List[TicketResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# PROFILE & TEAM MEMBERSHIP SCHEMAS
# =============================================================================

class ProfileMeResponse(BaseModel):
    profile_id: uuid.UUID
    email: str
    organization_id: uuid.UUID
    organization_slug: str
    role: str


class MemberInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=150)
    role: str = Field(default="supervisor", pattern="^(admin|supervisor)$")


class MemberRoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., pattern="^(admin|supervisor|owner)$")


class MemberResponse(BaseModel):
    profile_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
