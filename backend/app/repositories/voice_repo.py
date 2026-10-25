import uuid
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.voice import CallSession, CallEvent, Transcript, CallSummary
from app.models.base import utc_now

class VoiceRepository:
    async def create_session(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        room_name: str,
        business_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        status: str = "initiating",
        metadata: Optional[Dict[str, Any]] = None
    ) -> CallSession:
        session = CallSession(
            organization_id=org_id,
            business_id=business_id,
            customer_id=customer_id,
            room_name=room_name,
            status=status,
            handoff_state="none",
            started_at=utc_now(),
            custom_metadata=metadata or {}
        )
        db.add(session)
        await db.flush()
        return session

    async def get_session_by_id(
        self, db: AsyncSession, session_id: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Optional[CallSession]:
        stmt = select(CallSession).options(
            selectinload(CallSession.summary)
        ).where(CallSession.id == session_id)
        if org_id:
            stmt = stmt.where(CallSession.organization_id == org_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_session_by_room(self, db: AsyncSession, room_name: str) -> Optional[CallSession]:
        stmt = select(CallSession).options(
            selectinload(CallSession.summary)
        ).where(CallSession.room_name == room_name)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def update_status(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        status: str,
        handoff_state: Optional[str] = None,
        termination_reason: Optional[str] = None
    ) -> Optional[CallSession]:
        stmt = select(CallSession).where(CallSession.id == session_id)
        result = await db.execute(stmt)
        call = result.scalars().first()
        if not call:
            return None

        call.status = status
        if handoff_state:
            call.handoff_state = handoff_state
        if termination_reason:
            call.termination_reason = termination_reason

        if status in ("completed", "failed"):
            call.ended_at = utc_now()
            if call.started_at:
                started = call.started_at.replace(tzinfo=timezone.utc) if call.started_at.tzinfo is None else call.started_at
                ended = call.ended_at.replace(tzinfo=timezone.utc) if call.ended_at.tzinfo is None else call.ended_at
                call.duration_seconds = max(0, int((ended - started).total_seconds()))

        await db.flush()
        return call

    async def list_active_calls(self, db: AsyncSession, org_id: uuid.UUID) -> List[CallSession]:
        active_statuses = ["initiating", "active", "escalated", "supervisor_takeover"]
        stmt = select(CallSession).options(
            selectinload(CallSession.summary)
        ).where(
            CallSession.organization_id == org_id,
            CallSession.status.in_(active_statuses)
        ).order_by(CallSession.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_call_history(
        self, db: AsyncSession, org_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> Tuple[List[CallSession], int]:
        query = select(CallSession).where(CallSession.organization_id == org_id)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = query.options(
            selectinload(CallSession.summary)
        ).order_by(CallSession.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await db.execute(stmt)).scalars().all())

        return items, total

    async def add_event(
        self, db: AsyncSession, session_id: uuid.UUID, event_type: str, actor: str, payload: Optional[Dict[str, Any]] = None
    ) -> CallEvent:
        event = CallEvent(
            call_session_id=session_id,
            event_type=event_type,
            actor=actor,
            payload=payload or {}
        )
        db.add(event)
        await db.flush()
        return event

    async def get_events(self, db: AsyncSession, session_id: uuid.UUID) -> List[CallEvent]:
        stmt = select(CallEvent).where(CallEvent.call_session_id == session_id).order_by(CallEvent.created_at.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def add_transcript_turn(
        self, db: AsyncSession, session_id: uuid.UUID, org_id: uuid.UUID, speaker: str, content: str
    ) -> Transcript:
        turn = Transcript(
            call_session_id=session_id,
            organization_id=org_id,
            speaker=speaker,
            content=content,
            is_purged=False
        )
        db.add(turn)
        await db.flush()
        return turn

    async def get_transcripts(self, db: AsyncSession, session_id: uuid.UUID) -> List[Transcript]:
        stmt = select(Transcript).where(Transcript.call_session_id == session_id).order_by(Transcript.created_at.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def purge_expired_transcripts(self, db: AsyncSession, retention_days: int) -> int:
        """Purges transcript content older than retention_days while preserving audit records."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        stmt = update(Transcript).where(
            Transcript.created_at < cutoff,
            Transcript.is_purged == False  # noqa: E712
        ).values(
            content="[PURGED_BY_RETENTION_POLICY]",
            is_purged=True,
            purged_at=utc_now()
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount

    async def upsert_summary(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        org_id: uuid.UUID,
        summary_text: str,
        intent: Optional[str] = None,
        sentiment: Optional[str] = None,
        follow_up: bool = False
    ) -> CallSummary:
        stmt = select(CallSummary).where(CallSummary.call_session_id == session_id)
        result = await db.execute(stmt)
        summary = result.scalars().first()

        if summary:
            summary.summary = summary_text
            summary.primary_intent = intent
            summary.detected_sentiment = sentiment
            summary.follow_up_required = follow_up
        else:
            summary = CallSummary(
                call_session_id=session_id,
                organization_id=org_id,
                summary=summary_text,
                primary_intent=intent,
                detected_sentiment=sentiment,
                follow_up_required=follow_up
            )
            db.add(summary)

        await db.flush()
        return summary

voice_repo = VoiceRepository()
