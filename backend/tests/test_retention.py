import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.voice_repo import voice_repo
from app.services.retention_service import retention_service
from app.models.voice import Transcript

@pytest.mark.asyncio
async def test_30_day_transcript_retention_purge(db_session: AsyncSession, org_a):
    call = await voice_repo.create_session(
        db_session, org_id=org_a.id, room_name="retention-test-room"
    )

    # 1. Create expired turn (35 days old)
    old_turn = Transcript(
        call_session_id=call.id,
        organization_id=org_a.id,
        speaker="customer",
        content="Secret customer info from 35 days ago",
        is_purged=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=35)
    )
    # 2. Create unexpired turn (2 days old)
    recent_turn = Transcript(
        call_session_id=call.id,
        organization_id=org_a.id,
        speaker="customer",
        content="Recent inquiry content from 2 days ago",
        is_purged=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    db_session.add_all([old_turn, recent_turn])
    await db_session.flush()

    # Run 30-day retention purge
    purged_count = await retention_service.purge_expired_transcripts(db_session, retention_days=30)
    assert purged_count == 1

    # Verify old turn was purged
    await db_session.refresh(old_turn)
    assert old_turn.is_purged is True
    assert old_turn.content == "[PURGED_BY_RETENTION_POLICY]"
    assert old_turn.purged_at is not None

    # Verify recent turn was NOT purged
    await db_session.refresh(recent_turn)
    assert recent_turn.is_purged is False
    assert recent_turn.content == "Recent inquiry content from 2 days ago"
    assert recent_turn.purged_at is None
