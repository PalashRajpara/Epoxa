import uuid
import secrets
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.voice_repo import voice_repo
from app.repositories.customer_repo import customer_repo
from app.integrations.livekit import livekit_service
from app.agents.orchestrator import orchestrator
from app.models.voice import CallSession, Transcript, CallEvent
from app.schemas.voice import VoiceTokenResponse
from app.core.exceptions import ResourceNotFoundError
from app.core.config import settings

class VoiceService:
    async def initiate_session(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        business_id: Optional[uuid.UUID] = None
    ) -> VoiceTokenResponse:
        # Match or identify customer if phone provided
        customer_id: Optional[uuid.UUID] = None
        if customer_phone:
            matched = await customer_repo.find_match(db, org_id=org_id, phone=customer_phone)
            if matched:
                customer_id = matched.id

        room_name = f"epoxa-room-{secrets.token_hex(6)}"
        session = await voice_repo.create_session(
            db,
            org_id=org_id,
            room_name=room_name,
            business_id=business_id,
            customer_id=customer_id,
            status="active",
            metadata={"customer_name": customer_name or "Guest"}
        )

        # Generate participant identity
        participant_id = f"cust_{str(session.id)[:8]}"
        display_name = customer_name or "Customer"

        token = livekit_service.generate_token(
            room_name=room_name,
            participant_identity=participant_id,
            participant_name=display_name,
            ttl_seconds=900
        )

        return VoiceTokenResponse(
            token=token,
            room_name=room_name,
            session_id=session.id,
            livekit_url=settings.LIVEKIT_URL or "wss://epoxa-demo.livekit.cloud",
            expires_in_seconds=900,
            created_at=session.created_at
        )

    async def get_session(self, db: AsyncSession, org_id: uuid.UUID, session_id: uuid.UUID) -> CallSession:
        session = await voice_repo.get_session_by_id(db, session_id=session_id, org_id=org_id)
        if not session:
            raise ResourceNotFoundError("CallSession", session_id)
        return session

    async def end_session(
        self, db: AsyncSession, org_id: uuid.UUID, session_id: uuid.UUID, reason: str = "completed"
    ) -> CallSession:
        call = await self.get_session(db, org_id=org_id, session_id=session_id)
        updated = await voice_repo.update_status(db, session_id=session_id, status="completed", termination_reason=reason)
        # Attempt summary generation without rolling back call status on LLM error
        try:
            await orchestrator.generate_call_summary(db, org_id=org_id, session_id=session_id)
        except Exception as e:
            logger.warning("Call summary generation skipped or failed", error=str(e), session_id=str(session_id))
        await voice_repo.add_event(db, session_id=session_id, event_type="session_ended", actor="system", payload={"reason": reason})
        return updated or call

    async def process_speech_turn(
        self, db: AsyncSession, org_id: uuid.UUID, session_id: uuid.UUID, user_speech: str
    ) -> str:
        call = await self.get_session(db, org_id=org_id, session_id=session_id)
        if call.status == "initiating":
            call = await voice_repo.update_status(db, session_id=session_id, status="active")
        return await orchestrator.handle_turn(
            db, org_id=org_id, session_id=session_id, user_speech=user_speech, customer_id=call.customer_id
        )

    async def list_active_calls(self, db: AsyncSession, org_id: uuid.UUID) -> List[CallSession]:
        return await voice_repo.list_active_calls(db, org_id=org_id)

    async def list_call_history(
        self, db: AsyncSession, org_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> Tuple[List[CallSession], int]:
        return await voice_repo.list_call_history(db, org_id=org_id, page=page, page_size=page_size)

    async def get_transcripts(self, db: AsyncSession, org_id: uuid.UUID, session_id: uuid.UUID) -> List[Transcript]:
        # Validate session belongs to organization
        await self.get_session(db, org_id=org_id, session_id=session_id)
        return await voice_repo.get_transcripts(db, session_id=session_id)

voice_service = VoiceService()
