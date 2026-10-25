import uuid
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.voice_repo import voice_repo
from app.repositories.ticket_repo import ticket_repo
from app.integrations.livekit import livekit_service
from app.schemas.ticket import TicketCreate
from app.core.exceptions import ResourceNotFoundError, ConflictError
from app.core.logging import logger

from app.core.config import settings

class HandoffService:
    async def request_takeover(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        session_id: uuid.UUID,
        supervisor_id: uuid.UUID,
        supervisor_name: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Allows an authorized supervisor to take over an active or escalated call."""
        call = await voice_repo.get_session_by_id(db, session_id=session_id, org_id=org_id)
        if not call:
            raise ResourceNotFoundError("CallSession", session_id)

        livekit_url = settings.LIVEKIT_URL or "wss://epoxa-dnmkm636.livekit.cloud"
        metadata = dict(call.custom_metadata or {})
        assigned_supervisor = metadata.get("supervisor_id")

        # Concurrency guard: check if already taken over by another supervisor
        if call.status == "supervisor_takeover":
            if assigned_supervisor and str(assigned_supervisor) != str(supervisor_id):
                raise ConflictError("Call is already being handled by another supervisor")
            token = livekit_service.generate_token(
                room_name=call.room_name,
                participant_identity=f"sup_{str(supervisor_id)[:8]}",
                participant_name=f"Supervisor {supervisor_name}",
                is_supervisor=True,
                ttl_seconds=1800
            )
            return {
                "status": "supervisor_takeover",
                "room_name": call.room_name,
                "token": token,
                "livekit_url": livekit_url,
                "message": "Supervisor takeover active; token re-issued."
            }

        if call.status in ("completed", "failed"):
            raise ConflictError("Cannot take over a completed or terminated call")

        # Record supervisor assignment in metadata
        metadata["supervisor_id"] = str(supervisor_id)
        metadata["supervisor_name"] = supervisor_name
        call.custom_metadata = metadata

        # 1. Update call session state
        await voice_repo.update_status(
            db,
            session_id=session_id,
            status="supervisor_takeover",
            handoff_state="accepted"
        )

        # 2. Update active escalation if exists
        esc = await ticket_repo.get_active_escalation(db, session_id=session_id, org_id=org_id)
        if esc:
            await ticket_repo.update_escalation_state(db, escalation=esc, state="handoff_complete")

        # 3. Log takeover event
        await ticket_repo.log_takeover_event(
            db,
            org_id=org_id,
            session_id=session_id,
            supervisor_id=supervisor_id,
            action="takeover_started",
            notes=notes
        )
        await voice_repo.add_event(
            db,
            session_id=session_id,
            event_type="supervisor_takeover",
            actor="supervisor",
            payload={"supervisor_id": str(supervisor_id), "supervisor_name": supervisor_name}
        )
        await voice_repo.add_transcript_turn(
            db,
            session_id=session_id,
            org_id=org_id,
            speaker="ai_agent",
            content="[Announcement] A live customer support supervisor has joined the call. Epoxa AI is paused."
        )

        # 4. Generate supervisor LiveKit room token
        token = livekit_service.generate_token(
            room_name=call.room_name,
            participant_identity=f"sup_{str(supervisor_id)[:8]}",
            participant_name=f"Supervisor {supervisor_name}",
            is_supervisor=True,
            ttl_seconds=1800
        )

        return {
            "status": "supervisor_takeover",
            "room_name": call.room_name,
            "token": token,
            "livekit_url": livekit_url,
            "message": "Supervisor takeover active; AI audio suppressed."
        }

    async def handback_to_ai(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        session_id: uuid.UUID,
        supervisor_id: uuid.UUID,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Hands the conversation control back to the AI assistant."""
        call = await voice_repo.get_session_by_id(db, session_id=session_id, org_id=org_id)
        if not call:
            raise ResourceNotFoundError("CallSession", session_id)

        if call.status != "supervisor_takeover":
            raise ConflictError("Call is not currently in supervisor takeover state")

        # 1. Update call session state
        metadata = dict(call.custom_metadata or {})
        metadata.pop("supervisor_id", None)
        metadata.pop("supervisor_name", None)
        call.custom_metadata = metadata

        await voice_repo.update_status(
            db,
            session_id=session_id,
            status="active",
            handoff_state="returned_to_ai"
        )

        # 2. Log event & transcript turn
        await voice_repo.add_transcript_turn(
            db,
            session_id=session_id,
            org_id=org_id,
            speaker="ai_agent",
            content="[Announcement] Epoxa AI has resumed call control and is ready to assist you."
        )

        # 2. Log event
        await ticket_repo.log_takeover_event(
            db,
            org_id=org_id,
            session_id=session_id,
            supervisor_id=supervisor_id,
            action="handback_to_ai",
            notes=notes
        )
        await voice_repo.add_event(
            db,
            session_id=session_id,
            event_type="handback_to_ai",
            actor="supervisor",
            payload={"notes": notes or ""}
        )

        return {
            "status": "active",
            "handoff_state": "returned_to_ai",
            "message": "Call control successfully returned to AI assistant."
        }

    async def create_fallback_ticket_if_unavailable(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        session_id: uuid.UUID,
        reason: str = "No supervisor available for live takeover"
    ) -> Dict[str, Any]:
        """Creates an urgent follow-up ticket when live escalation cannot be answered."""
        call = await voice_repo.get_session_by_id(db, session_id=session_id, org_id=org_id)
        if not call:
            raise ResourceNotFoundError("CallSession", session_id)

        ticket = await ticket_repo.create_ticket(
            db,
            org_id=org_id,
            data=TicketCreate(
                title="Unanswered Escalation Follow-up",
                description=f"Customer requested live assistance during voice call. Reason: {reason}",
                category="escalation",
                priority="urgent",
                call_session_id=session_id,
                customer_id=call.customer_id
            )
        )

        esc = await ticket_repo.get_active_escalation(db, session_id=session_id, org_id=org_id)
        if esc:
            await ticket_repo.update_escalation_state(
                db, escalation=esc, state="fallback_ticket_created", ticket_id=ticket.id
            )

        await voice_repo.add_event(
            db,
            session_id=session_id,
            event_type="fallback_ticket_created",
            actor="system",
            payload={"ticket_number": ticket.ticket_number}
        )

        return {
            "fallback_created": True,
            "ticket_number": ticket.ticket_number,
            "status": ticket.status
        }

handoff_service = HandoffService()
