import uuid
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_supervisor
from app.services.voice_service import voice_service
from app.services.handoff_service import handoff_service
from app.schemas.voice import CallSessionRead, TranscriptRead
from app.schemas.auth import SupervisorContext
from app.schemas.common import PaginatedResponse
from app.schemas.ticket import TakeoverActionRequest

router = APIRouter(prefix="/calls", tags=["Call Sessions & Handoff"])

@router.get("/active", response_model=List[CallSessionRead], summary="List active calls for supervisor dashboard")
async def list_active_calls(
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await voice_service.list_active_calls(db, org_id=supervisor.organization_id)

@router.get("/history", response_model=PaginatedResponse[CallSessionRead], summary="List historical calls with summaries")
async def list_call_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    items, total = await voice_service.list_call_history(
        db, org_id=supervisor.organization_id, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{session_id}", response_model=CallSessionRead, summary="Get call session details")
async def get_call_session(
    session_id: uuid.UUID,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await voice_service.get_session(db, org_id=supervisor.organization_id, session_id=session_id)

@router.get("/{session_id}/transcripts", response_model=List[TranscriptRead], summary="Get transcripts for call session")
async def get_transcripts(
    session_id: uuid.UUID,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await voice_service.get_transcripts(db, org_id=supervisor.organization_id, session_id=session_id)

@router.get("/{session_id}/token", summary="Get supervisor LiveKit room token")
async def get_supervisor_token(
    session_id: uuid.UUID,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    from app.core.config import settings
    from app.integrations.livekit import livekit_service
    call = await voice_service.get_session(db, org_id=supervisor.organization_id, session_id=session_id)
    token = livekit_service.generate_token(
        room_name=call.room_name,
        participant_identity=f"sup_{str(supervisor.user_id)[:8]}",
        participant_name=f"Supervisor {supervisor.full_name}",
        is_supervisor=True,
        ttl_seconds=1800
    )
    return {
        "token": token,
        "room_name": call.room_name,
        "livekit_url": settings.LIVEKIT_URL or "wss://epoxa-dnmkm636.livekit.cloud"
    }

@router.post("/{session_id}/takeover", summary="Supervisor takes over live call")
async def takeover_call(
    session_id: uuid.UUID,
    req: TakeoverActionRequest,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await handoff_service.request_takeover(
        db,
        org_id=supervisor.organization_id,
        session_id=session_id,
        supervisor_id=supervisor.user_id,
        supervisor_name=supervisor.full_name,
        notes=req.notes
    )

@router.post("/{session_id}/handback", summary="Supervisor returns call control to AI")
async def handback_call(
    session_id: uuid.UUID,
    req: TakeoverActionRequest,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await handoff_service.handback_to_ai(
        db,
        org_id=supervisor.organization_id,
        session_id=session_id,
        supervisor_id=supervisor.user_id,
        notes=req.notes
    )

@router.post("/{session_id}/fallback-ticket", summary="Create fallback ticket when supervisor unavailable")
async def fallback_ticket(
    session_id: uuid.UUID,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await handoff_service.create_fallback_ticket_if_unavailable(
        db, org_id=supervisor.organization_id, session_id=session_id
    )

@router.post("/{session_id}/end", response_model=CallSessionRead, summary="Supervisor forces end of call session")
async def supervisor_end_call(
    session_id: uuid.UUID,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    return await voice_service.end_session(
        db, org_id=supervisor.organization_id, session_id=session_id, reason="supervisor_terminated"
    )

class SupervisorTurnRequest(BaseModel):
    speech: str
    audio_base64: Optional[str] = None
    mime_type: Optional[str] = "audio/webm"

@router.post("/{session_id}/supervisor-turn", summary="Supervisor sends speech turn to customer")
async def supervisor_speech_turn(
    session_id: uuid.UUID,
    req: SupervisorTurnRequest,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    import base64
    from app.repositories.voice_repo import voice_repo
    from app.integrations.speech import speech_service
    from app.core.logging import logger

    # Validate session belongs to organization
    await voice_service.get_session(db, org_id=supervisor.organization_id, session_id=session_id)

    audio_b64 = req.audio_base64
    mime_type = req.mime_type or "audio/webm"
    is_human = bool(req.audio_base64)
    if req.audio_base64 == "LIVE_HUMAN_WEBRTC":
        audio_b64 = None
        is_human = True
    speech_text = req.speech.strip() or ("(Live Supervisor Voice)" if is_human else "")

    # Only synthesize AI voice if supervisor typed text (not speaking live over WebRTC)
    if not is_human and not audio_b64 and speech_text:
        try:
            audio_bytes = await speech_service.synthesize_speech(speech_text, voice="aura-helios-en")
            if audio_bytes and len(audio_bytes) > 200:
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                mime_type = "audio/mpeg"
        except Exception as e:
            logger.warning("Supervisor speech synthesis error", error=str(e))

    # Persist turn
    turn = await voice_repo.add_transcript_turn(
        db,
        session_id=session_id,
        org_id=supervisor.organization_id,
        speaker="supervisor",
        content=speech_text or "(Live Supervisor Voice)"
    )
    await voice_repo.add_event(
        db,
        session_id=session_id,
        event_type="supervisor_speech",
        actor="supervisor",
        payload={
            "turn_id": str(turn.id),
            "text": speech_text or "(Live Supervisor Voice)",
            "audio_base64": audio_b64,
            "mime_type": mime_type,
            "is_human": is_human
        }
    )

    return {
        "message": "Supervisor turn recorded",
        "turn_id": str(turn.id),
        "content": speech_text or "(Live Supervisor Voice)",
        "audio_base64": audio_b64,
        "mime_type": mime_type,
        "is_human": is_human
    }
