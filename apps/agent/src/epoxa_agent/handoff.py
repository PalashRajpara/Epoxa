"""Authoritative handoff management for Epoxa Voice Agent."""

from typing import Dict, Optional
import structlog
from epoxa_core.database import get_session_factory
from epoxa_core.models.entities import CallSession
from sqlalchemy import select, update

logger = structlog.get_logger("epoxa_agent.handoff")

# In-process cache: session_id -> handoff_state ("ai", "human_pending", "human_active")
_handoff_cache: Dict[str, str] = {}

def get_cached_handoff_state(session_id: str) -> str:
    """Fast in-process lookup for audio path (no DB latency)."""
    return _handoff_cache.get(session_id, "ai")

def is_ai_silenced(session_id: str) -> bool:
    """Returns True if human takeover is active or pending."""
    state = get_cached_handoff_state(session_id)
    return state in ("human_pending", "human_active")

def update_local_handoff_cache(session_id: str, state: str) -> None:
    _handoff_cache[session_id] = state
    logger.info("local_handoff_cache_updated", session_id=session_id, state=state)

async def refresh_authoritative_handoff_state(session_id: str) -> str:
    """Fetch authoritative state from PostgreSQL and sync local cache."""
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            stmt = select(CallSession.handoff_state).where(CallSession.id == session_id)
            result = await session.execute(stmt)
            state = result.scalar_one_or_none() or "ai"
            _handoff_cache[session_id] = state
            return state
    except Exception as e:
        logger.error("failed_to_refresh_authoritative_handoff", session_id=session_id, error=str(e))
        return _handoff_cache.get(session_id, "ai")

async def set_authoritative_handoff_state(session_id: str, state: str) -> None:
    """Write authoritative state to PostgreSQL and update local cache."""
    _handoff_cache[session_id] = state
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            async with session.begin():
                stmt = (
                    update(CallSession)
                    .where(CallSession.id == session_id)
                    .values(handoff_state=state)
                )
                await session.execute(stmt)
        logger.info("authoritative_handoff_persisted", session_id=session_id, state=state)
    except Exception as e:
        logger.error("failed_to_persist_handoff_state", session_id=session_id, state=state, error=str(e))
