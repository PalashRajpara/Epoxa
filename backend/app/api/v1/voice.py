import uuid
import base64
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_public_organization
from app.services.voice_service import voice_service
from app.integrations.speech import speech_service
from app.core.logging import logger
from app.schemas.voice import VoiceTokenRequest, VoiceTokenResponse, CallSessionRead
from app.models.tenant import Organization

router = APIRouter(prefix="/voice", tags=["Customer Voice Experience"])

class SpeechTurnRequest(BaseModel):
    speech: str

class SpeechTurnResponse(BaseModel):
    reply: str
    audio_base64: Optional[str] = None

class GreetingResponse(BaseModel):
    greeting: str
    audio_base64: Optional[str] = None

@router.get("/greeting", response_model=GreetingResponse, summary="Get greeting text and high-fidelity Deepgram audio")
async def get_greeting(
    name: Optional[str] = Query(None),
    session_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    caller_display = name.strip() if name and name.strip() else "there"
    text = f"Hello {caller_display}! Thank you for calling Apex Global Retail. I am Epoxa AI. How can I help you with your order, shipping, or returns today?"
    audio_b64 = None
    try:
        audio_bytes = await speech_service.synthesize_speech(text)
        if audio_bytes and len(audio_bytes) > 200:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        logger.warning("Greeting speech synthesis error", error=str(e))

    if session_id:
        from app.repositories.voice_repo import voice_repo
        await voice_repo.update_status(db, session_id=session_id, status="active")

    return GreetingResponse(greeting=text, audio_base64=audio_b64)

@router.post("/speak", summary="Synthesize speech audio via Deepgram Aura")
async def synthesize_speech_endpoint(req: SpeechTurnRequest):
    audio_bytes = await speech_service.synthesize_speech(req.speech)
    return Response(content=audio_bytes, media_type="audio/mpeg")

@router.post("/token", response_model=VoiceTokenResponse, summary="Initiate customer call & get LiveKit token")
async def create_voice_token(
    req: VoiceTokenRequest,
    org: Organization = Depends(get_public_organization),
    db: AsyncSession = Depends(get_db)
):
    return await voice_service.initiate_session(
        db,
        org_id=org.id,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        business_id=req.business_id
    )

@router.get("/sessions/{session_id}", response_model=CallSessionRead, summary="Get customer call session state")
async def get_customer_session(
    session_id: uuid.UUID,
    org: Organization = Depends(get_public_organization),
    db: AsyncSession = Depends(get_db)
):
    return await voice_service.get_session(db, org_id=org.id, session_id=session_id)

@router.post("/sessions/{session_id}/turn", response_model=SpeechTurnResponse, summary="Process speech turn")
async def process_turn(
    session_id: uuid.UUID,
    req: SpeechTurnRequest,
    org: Organization = Depends(get_public_organization),
    db: AsyncSession = Depends(get_db)
):
    reply = await voice_service.process_speech_turn(
        db, org_id=org.id, session_id=session_id, user_speech=req.speech
    )
    audio_b64 = None
    try:
        audio_bytes = await speech_service.synthesize_speech(reply)
        if audio_bytes and len(audio_bytes) > 200:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        logger.warning("Speech turn synthesis error", error=str(e))

    return SpeechTurnResponse(reply=reply, audio_base64=audio_b64)

@router.post("/sessions/{session_id}/end", response_model=CallSessionRead, summary="End customer call session")
async def end_call(
    session_id: uuid.UUID,
    org: Organization = Depends(get_public_organization),
    db: AsyncSession = Depends(get_db)
):
    return await voice_service.end_session(db, org_id=org.id, session_id=session_id)

@router.get("/sessions/{session_id}/supervisor-turns", summary="Get recent supervisor turns for customer session")
async def get_customer_supervisor_turns(
    session_id: uuid.UUID,
    org: Organization = Depends(get_public_organization),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.voice_repo import voice_repo
    events = await voice_repo.get_events(db, session_id=session_id)
    supervisor_speech_events = [
        ev for ev in events if ev.event_type == "supervisor_speech"
    ]
    return [
        {
            "id": str(ev.id),
            "turn_id": ev.payload.get("turn_id"),
            "content": ev.payload.get("text", ""),
            "audio_base64": ev.payload.get("audio_base64"),
            "mime_type": ev.payload.get("mime_type", "audio/mpeg"),
            "is_human": ev.payload.get("is_human", False),
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in supervisor_speech_events
    ]


