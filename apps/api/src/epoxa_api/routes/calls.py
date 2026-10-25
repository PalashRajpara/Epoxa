"""
Call session API endpoints: public call initiation, supervisor takeover, and real-time SSE stream.
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator, List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sse_starlette.sse import EventSourceResponse

from epoxa_api.auth.dependencies import (
    AuthenticatedContext,
    get_authenticated_context,
    require_role,
)
from epoxa_api.schemas import (
    CallSessionListResponse,
    CallSessionResponse,
    CallStartRequest,
    CallStartResponse,
    CallTakeoverResponse,
    TranscriptTurnResponse,
)
from epoxa_core.exceptions import EntityNotFoundError
from epoxa_core.services.call_session_service import CallSessionService
from epoxa_core.services.customer_service import CustomerService
from epoxa_core.uow import UnitOfWork

router = APIRouter(prefix="/calls", tags=["Calls"])


# =============================================================================
# PUBLIC CALL START (Rate-limited, unguessable room, restricted audio token)
# =============================================================================

@router.post("", response_model=CallStartResponse)
async def start_public_call(
    request: Request,
    body: CallStartRequest,
) -> CallStartResponse:
    """
    Public entrypoint for callers:
    1. Resolves default tenant organization (Epoxcel).
    2. Validates rate limit and concurrent call capacity.
    3. Generates an unguessable room and mints a short-lived audio-only token.
    """
    async with UnitOfWork() as uow:
        # Load default organization
        org = await uow.organizations.get_by_slug("voice-ai-agent") or await uow.organizations.get_by_slug("epoxcel")
        if not org:
            # Fallback to first available organization
            all_orgs = await uow.organizations.list_all(limit=1)
            if not all_orgs:
                raise EntityNotFoundError("Organization", "voice-ai-agent")
            org = all_orgs[0]

        customer_id: Optional[uuid.UUID] = None
        if body.phone:
            cust_service = CustomerService(uow)
            customer = await cust_service.verify_by_phone(org.id, body.phone)
            if customer:
                customer_id = customer.id

        session_service = CallSessionService(uow)
        result = await session_service.start_call(
            organization_id=org.id,
            participant_name=body.participant_name,
            customer_id=customer_id,
        )

        return CallStartResponse(
            session_id=result["session_id"],
            room_name=result["room_name"],
            token=result["token"],
            livekit_url=result["livekit_url"],
            identity=result["identity"],
        )


# =============================================================================
# SUPERVISOR AUTHENTICATED ENDPOINTS
# =============================================================================

@router.get("", response_model=CallSessionListResponse)
async def list_calls(
    status: Optional[str] = Query(None, description="Filter by status ('active', 'escalated', 'completed')"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> CallSessionListResponse:
    """Lists call sessions for the supervisor's organization."""
    async with UnitOfWork() as uow:
        sessions = await uow.call_sessions.list_by_org(
            organization_id=ctx.organization_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return CallSessionListResponse(
            sessions=[
                CallSessionResponse(
                    id=s.id,
                    room_name=s.room_name,
                    participant_name=s.participant_name,
                    status=s.status,
                    handoff_state=s.handoff_state,
                    started_at=s.started_at,
                    ended_at=s.ended_at,
                    duration_seconds=s.duration_seconds,
                    summary=s.summary,
                    end_reason=s.end_reason,
                    agent_version=s.agent_version,
                    llm_model=s.llm_model,
                )
                for s in sessions
            ],
            total=len(sessions),
            limit=limit,
            offset=offset,
        )


@router.get("/stream")
async def stream_live_calls(
    request: Request,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> EventSourceResponse:
    """
    Server-Sent Events (SSE) endpoint providing real-time call updates.
    Replaces 3-second and 1.5-second client polling.
    """
    async def event_generator() -> AsyncGenerator[Dict[str, str], None]:
        while True:
            if await request.is_disconnected():
                break

            async with UnitOfWork() as uow:
                active_sessions = await uow.call_sessions.list_active(ctx.organization_id)
                data = [
                    {
                        "id": str(s.id),
                        "room_name": s.room_name,
                        "participant_name": s.participant_name,
                        "status": s.status,
                        "handoff_state": s.handoff_state,
                        "started_at": s.started_at.isoformat(),
                        "duration_seconds": s.duration_seconds,
                    }
                    for s in active_sessions
                ]
                yield {
                    "event": "calls_update",
                    "data": json.dumps({"active_calls": data, "count": len(data)}),
                }

            await asyncio.sleep(2.0)

    return EventSourceResponse(event_generator())


@router.get("/{session_id}", response_model=CallSessionResponse)
async def get_call_session(
    session_id: uuid.UUID,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> CallSessionResponse:
    """Retrieves metadata for a specific call session."""
    async with UnitOfWork() as uow:
        session = await uow.call_sessions.get_by_id(session_id)
        if not session or session.organization_id != ctx.organization_id:
            raise EntityNotFoundError("CallSession", session_id)

        return CallSessionResponse(
            id=session.id,
            room_name=session.room_name,
            participant_name=session.participant_name,
            status=session.status,
            handoff_state=session.handoff_state,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_seconds=session.duration_seconds,
            summary=session.summary,
            end_reason=session.end_reason,
            agent_version=session.agent_version,
            llm_model=session.llm_model,
        )


@router.get("/{session_id}/transcript", response_model=List[TranscriptTurnResponse])
async def get_call_transcript(
    session_id: uuid.UUID,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> List[TranscriptTurnResponse]:
    """Retrieves full conversation transcript turns for a call session."""
    async with UnitOfWork() as uow:
        session = await uow.call_sessions.get_by_id(session_id)
        if not session or session.organization_id != ctx.organization_id:
            raise EntityNotFoundError("CallSession", session_id)

        turns = await uow.transcripts.get_by_session(session_id)
        return [
            TranscriptTurnResponse(
                id=turn.id,
                session_id=turn.session_id,
                sequence=turn.sequence,
                role=turn.role,
                speaker_identity=turn.speaker_identity,
                content=turn.content,
                spoken_at=turn.spoken_at,
            )
            for turn in turns
        ]


@router.post("/{session_id}/takeover", response_model=CallTakeoverResponse)
async def takeover_call(
    session_id: uuid.UUID,
    notes: Optional[str] = None,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> CallTakeoverResponse:
    """Server-authoritative human supervisor takeover."""
    async with UnitOfWork() as uow:
        service = CallSessionService(uow)
        result = await service.takeover_call(
            organization_id=ctx.organization_id,
            session_id=session_id,
            supervisor_profile_id=ctx.profile_id,
            supervisor_name=ctx.email.split("@")[0],
            notes=notes,
        )
        return CallTakeoverResponse(
            token=result["token"],
            identity=result["identity"],
            room_name=result["room_name"],
            handoff_state=result["handoff_state"],
        )


@router.post("/{session_id}/handback", response_model=CallSessionResponse)
async def handback_call(
    session_id: uuid.UUID,
    notes: Optional[str] = None,
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> CallSessionResponse:
    """Server-authoritative handback to AI."""
    async with UnitOfWork() as uow:
        service = CallSessionService(uow)
        session = await service.handback_call(
            organization_id=ctx.organization_id,
            session_id=session_id,
            supervisor_profile_id=ctx.profile_id,
            notes=notes,
        )
        return CallSessionResponse(
            id=session.id,
            room_name=session.room_name,
            participant_name=session.participant_name,
            status=session.status,
            handoff_state=session.handoff_state,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_seconds=session.duration_seconds,
            summary=session.summary,
            end_reason=session.end_reason,
            agent_version=session.agent_version,
            llm_model=session.llm_model,
        )


@router.post("/{session_id}/end", response_model=CallSessionResponse)
async def end_call(
    session_id: uuid.UUID,
    reason: str = Query("supervisor_ended", description="Disconnect rationale"),
    ctx: AuthenticatedContext = Depends(require_role("supervisor")),
) -> CallSessionResponse:
    """Cleanly terminates an active call session."""
    async with UnitOfWork() as uow:
        service = CallSessionService(uow)
        session = await service.end_call(
            organization_id=ctx.organization_id,
            session_id=session_id,
            reason=reason,
        )
        return CallSessionResponse(
            id=session.id,
            room_name=session.room_name,
            participant_name=session.participant_name,
            status=session.status,
            handoff_state=session.handoff_state,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_seconds=session.duration_seconds,
            summary=session.summary,
            end_reason=session.end_reason,
            agent_version=session.agent_version,
            llm_model=session.llm_model,
        )
