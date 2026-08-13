"""
agent/handoff.py
================
Manages the human escalation and handoff state for the voice AI agent.
Tracks whether the AI agent should remain silent (in handoff mode) and
synchronizes status changes with the Supabase PostgreSQL database. Also
provides helper functions to retrieve conversation transcripts for human agents.
"""

import logging
import os
import sys
from typing import List, Dict, Any

# Ensure backend path is added so we can import database connection models
# Since this file sits in ai-voice-agent/agent/handoff.py,
# the backend is at ai-voice-agent/backend.
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import get_supabase_client, get_full_transcript

logger = logging.getLogger("handoff")

# Global dictionary to track handoff states for active sessions in this worker process.
# Since each call runs in its own spawned worker process, this acts as a simple per-session flag.
_active_handoffs = {}

def set_handoff_active(session_id: str, active: bool) -> None:
    """
    Sets whether a call session is currently in handoff mode (meaning human has taken over).
    Also updates the status in Supabase so the dashboard and backend know the state of the call.
    """
    _active_handoffs[session_id] = active
    logger.info(f"[Handoff] Handoff status for session {session_id[:8]} set to: {active}")
    
    # Update Supabase status: 'escalated' means human has taken over, 'active' means AI handling
    status = "escalated" if active else "active"
    
    client = get_supabase_client()
    if not client:
        logger.warning("[Handoff] Supabase client is not available. Status update skipped.")
        return
        
    try:
        client.table("call_sessions").update({"status": status}).eq("id", session_id).execute()
        logger.info(f"[Handoff] DB status successfully updated to '{status}' for session {session_id[:8]}")
    except Exception as e:
        logger.error(f"[Handoff] Failed to update call session status in DB: {e}")


def is_handoff_active(session_id: str) -> bool:
    """
    Returns True if handoff mode is active for the given session ID,
    indicating that the AI agent should mute its voice responses.
    """
    return _active_handoffs.get(session_id, False)


def share_transcript(session_id: str) -> List[Dict[str, Any]]:
    """
    Fetches the complete conversation transcript for the specified session.
    Enables a human agent taking over the call to quickly read what has been discussed.
    """
    logger.info(f"[Handoff] Fetching full transcript for session {session_id[:8]}...")
    try:
        return get_full_transcript(session_id)
    except Exception as e:
        logger.error(f"[Handoff] Failed to retrieve transcript: {e}")
        return []
