"""
Call session service coordinating call lifecycle, room minting, takeover, and server-authoritative handback.
"""

import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from livekit import api as lk_api

from epoxa_core.exceptions import (
    AbuseLimitExceededError,
    EntityNotFoundError,
    HandoffStateError,
    ValidationError,
)
from epoxa_core.logging import get_logger
from epoxa_core.models.entities import AuditLog, CallSession, HandoffEvent
from epoxa_core.settings import settings
from epoxa_core.uow import UnitOfWork

logger = get_logger("epoxa_core.call_session_service")


class CallSessionService:
    """Manages WebRTC call sessions, token minting, and supervisor takeover transitions."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def _get_livekit_api(self) -> lk_api.LiveKitAPI:
        """Instantiates LiveKit Server API client."""
        return lk_api.LiveKitAPI(
            url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY.get_secret_value(),
            api_secret=settings.LIVEKIT_API_SECRET.get_secret_value(),
        )

    def mint_token(
        self,
        room_name: str,
        identity: str,
        name: str,
        role: str = "customer",
        ttl_seconds: int = 600,
    ) -> str:
        """Mints a least-privilege LiveKit WebRTC access token."""
        api_key = settings.LIVEKIT_API_KEY.get_secret_value()
        api_secret = settings.LIVEKIT_API_SECRET.get_secret_value()

        # Audio-only grants for customer; publish audio for supervisor
        is_supervisor = role in ("supervisor", "agent")
        grants = lk_api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
            can_publish_sources=["microphone"] if not is_supervisor else None,
        )

        token = (
            lk_api.AccessToken(api_key=api_key, api_secret=api_secret)
            .with_identity(identity)
            .with_name(name)
            .with_ttl(timedelta(seconds=ttl_seconds))
            .with_grants(grants)
        )
        return str(token.to_jwt())

    async def start_call(
        self,
        organization_id: uuid.UUID,
        participant_name: str,
        customer_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Creates a call session, generates an unguessable room, enforces the concurrent call cap,
        and returns a restricted audio-only token for the customer.
        """
        # 1. Enforce global concurrent call cap (D7)
        active_count = await self.uow.call_sessions.count_active_calls(organization_id)
        if active_count >= settings.CONCURRENT_CALL_CAP:
            raise AbuseLimitExceededError(
                f"Maximum concurrent calls reached ({settings.CONCURRENT_CALL_CAP}). Please try again shortly.",
                limit_type="concurrent_cap",
            )

        # 2. Generate cryptographically unguessable room name
        room_name = f"call_{secrets.token_urlsafe(16)}"
        participant_identity = f"cust_{secrets.token_hex(6)}"

        # 3. Create database call session
        session = CallSession(
            organization_id=organization_id,
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name=participant_name.strip() or "Caller",
            customer_id=customer_id,
            status="active",
            handoff_state="ai",
            agent_version="1.0.0",
            prompt_version="v1",
            llm_model=settings.LLM_MODEL,
        )
        self.uow.call_sessions.add(session)
        await self.uow.commit()

        # 4. Mint customer token (TTL 10 min)
        token = self.mint_token(
            room_name=room_name,
            identity=participant_identity,
            name=participant_name.strip() or "Caller",
            role="customer",
            ttl_seconds=settings.MAX_CALL_DURATION_MINUTES * 60,
        )

        logger.info("New call session created", session_id=str(session.id), room_name=room_name)

        return {
            "session_id": str(session.id),
            "room_name": room_name,
            "token": token,
            "livekit_url": settings.LIVEKIT_URL,
            "identity": participant_identity,
        }

    async def takeover_call(
        self,
        organization_id: uuid.UUID,
        session_id: uuid.UUID,
        supervisor_profile_id: uuid.UUID,
        supervisor_name: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Server-authoritative supervisor takeover."""
        session = await self.uow.call_sessions.get_by_id(session_id)
        if not session or session.organization_id != organization_id:
            raise EntityNotFoundError("CallSession", session_id)

        if session.status not in ("active", "escalated"):
            raise HandoffStateError(session.status, "takeover")

        # 1. Update session handoff state
        session.handoff_state = "human_active"
        session.status = "escalated"

        # 2. Record append-only handoff event
        event = HandoffEvent(
            session_id=session.id,
            profile_id=supervisor_profile_id,
            action="takeover",
            notes=notes,
        )
        self.uow.handoff_events.add(event)

        # 3. Record audit log
        audit = AuditLog(
            organization_id=organization_id,
            actor_profile_id=supervisor_profile_id,
            action="takeover_call",
            entity_type="call_session",
            entity_id=str(session.id),
            metadata_={"room_name": session.room_name},
        )
        self.uow.audit_logs.add(audit)
        await self.uow.commit()

        # 4. Mint supervisor LiveKit token
        supervisor_identity = f"agent_{secrets.token_hex(6)}"
        token = self.mint_token(
            room_name=session.room_name,
            identity=supervisor_identity,
            name=f"Supervisor {supervisor_name}",
            role="supervisor",
            ttl_seconds=7200,
        )

        return {
            "token": token,
            "identity": supervisor_identity,
            "room_name": session.room_name,
            "handoff_state": session.handoff_state,
        }

    async def handback_call(
        self,
        organization_id: uuid.UUID,
        session_id: uuid.UUID,
        supervisor_profile_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> CallSession:
        """Server-authoritative handback to AI."""
        session = await self.uow.call_sessions.get_by_id(session_id)
        if not session or session.organization_id != organization_id:
            raise EntityNotFoundError("CallSession", session_id)

        session.handoff_state = "ai"
        session.status = "active"

        # Record handoff event
        event = HandoffEvent(
            session_id=session.id,
            profile_id=supervisor_profile_id,
            action="return_to_ai",
            notes=notes,
        )
        self.uow.handoff_events.add(event)

        # Record audit log
        audit = AuditLog(
            organization_id=organization_id,
            actor_profile_id=supervisor_profile_id,
            action="handback_call",
            entity_type="call_session",
            entity_id=str(session.id),
        )
        self.uow.audit_logs.add(audit)
        await self.uow.commit()

        # Dispatch server-authoritative resume data packet via LiveKit Server API
        try:
            lk_client = self._get_livekit_api()
            async with lk_client as client:
                data_bytes = json.dumps({"action": "resume"}).encode("utf-8")
                await client.room.send_data(
                    lk_api.SendDataRequest(
                        room=session.room_name,
                        data=data_bytes,
                        kind=lk_api.DataPacket.Kind.RELIABLE,
                    )
                )
            logger.info("Sent server-authoritative resume packet to room", room_name=session.room_name)
        except Exception as e:
            logger.warning("Could not dispatch resume signal via LiveKit server API", error=str(e))

        return session

    async def end_call(
        self,
        organization_id: uuid.UUID,
        session_id: uuid.UUID,
        reason: str = "normal",
        summary: Optional[str] = None,
    ) -> CallSession:
        """Terminates a call session and calculates duration."""
        session = await self.uow.call_sessions.get_by_id(session_id)
        if not session or session.organization_id != organization_id:
            raise EntityNotFoundError("CallSession", session_id)

        now_utc = datetime.now(timezone.utc)
        duration = int((now_utc - session.started_at).total_seconds())

        session.status = "completed"
        session.ended_at = now_utc
        session.duration_seconds = max(duration, 0)
        session.end_reason = reason
        if summary:
            session.summary = summary

        await self.uow.commit()

        # Attempt to delete room on LiveKit server
        try:
            lk_client = self._get_livekit_api()
            async with lk_client as client:
                await client.room.delete_room(lk_api.DeleteRoomRequest(room=session.room_name))
        except Exception as e:
            logger.warning("Could not delete room on LiveKit server", error=str(e))

        return session
