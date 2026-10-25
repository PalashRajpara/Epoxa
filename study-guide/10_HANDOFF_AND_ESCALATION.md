# 10 — Human Handoff and Escalation: The Full Flow

> This is where LangGraph + LiveKit + Supabase + handoff.py all work together.
> Understanding escalation means understanding how the AI gracefully steps aside
> for a human — and how it can resume afterward.

---

## What Is Escalation?

**Escalation** is when the AI decides (or the customer requests) that a human agent
should take over the call. This can happen because:
1. The customer explicitly asks: "Let me speak to a human" / "Get me your manager"
2. Identity verification fails 3 times (security policy)
3. The backend database is unreachable (technical failure)
4. The complaint system is unavailable (technical failure)

**What should happen during escalation:**
1. AI speaks a transfer message: "I'm transferring you to a human agent. Please hold."
2. AI goes SILENT — it stops generating responses, even if the customer speaks
3. The human agent joins the LiveKit room (from the support dashboard)
4. Human and customer can now talk directly
5. The AI doesn't interfere — it can't hear the human agent's audio

**What should happen when the human wants the AI back:**
1. Human clicks "Resume AI" in the dashboard
2. Dashboard sends a data message to the LiveKit room
3. AI receives the message, clears the handoff flag
4. AI greets the customer to signal it's back
5. Normal conversation resumes

---

## The Handoff State — `agent/handoff.py`

```python
# agent/handoff.py

import logging, os, sys
from typing import List, Dict, Any

# Add the backend directory to sys.path so we can import database functions
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import get_supabase_client, get_full_transcript

logger = logging.getLogger("handoff")

# ─── THE IN-MEMORY FLAG ────────────────────────────────────────────────────────
# This is a simple Python dict. The keys are session IDs; values are True/False.
# {"abc-123": True, "xyz-789": False}
#
# Why a dict instead of a database lookup?
# Because is_handoff_active() is called before EVERY LLM response.
# A database lookup would add 50-200ms of latency to every single voice turn.
# An in-memory dict lookup is essentially instant (nanoseconds).
#
# The trade-off: if the worker process crashes and restarts, the in-memory state is lost.
# But since LiveKit rooms also don't survive worker crashes, this is acceptable.
_active_handoffs = {}


def set_handoff_active(session_id: str, active: bool) -> None:
    """
    Called when escalation starts (active=True) or when AI resumes (active=False).

    Two things happen:
    1. Update the in-memory flag (instant — for the LLM check)
    2. Update Supabase (slower — for the dashboard to see the status)
    """
    # Update in-memory state IMMEDIATELY
    _active_handoffs[session_id] = active
    logger.info(f"[Handoff] Handoff status for {session_id[:8]} set to: {active}")

    # Determine the status string for the database
    # True  → "escalated" (human is handling the call)
    # False → "active" (AI is back in control)
    status = "escalated" if active else "active"

    # Update Supabase so the dashboard reflects the change
    client = get_supabase_client()
    if not client:
        logger.warning("[Handoff] Supabase not available. Status update skipped.")
        return  # Graceful degradation: local flag still works

    try:
        # Find the call_sessions row for this session and update its status
        client.table("call_sessions").update({"status": status}).eq("id", session_id).execute()
        logger.info(f"[Handoff] DB status updated to '{status}' for session {session_id[:8]}")
    except Exception as e:
        logger.error(f"[Handoff] Failed to update DB status: {e}")
        # Don't re-raise — the call still works with the in-memory flag


def is_handoff_active(session_id: str) -> bool:
    """
    Returns True if the AI should be silent for this session.
    Called before EVERY LLM response in LangGraphStream._run().
    Uses in-memory dict (no network, instant).
    """
    return _active_handoffs.get(session_id, False)
    # .get(key, default) returns False if session_id is not in the dict
    # (which means handoff is not active — normal behavior)


def share_transcript(session_id: str) -> List[Dict[str, Any]]:
    """
    Fetches the full conversation transcript for this session.
    Used when a human agent takes over — they need to see what was already discussed.
    """
    try:
        return get_full_transcript(session_id)  # Supabase query
    except Exception as e:
        logger.error(f"[Handoff] Failed to retrieve transcript: {e}")
        return []
```

---

## How the AI Silences Itself — `agent/graph_builder.py`

```python
# agent/graph_builder.py — LangGraphStream._run()

async def _run(self) -> None:
    try:
        # ── THE HANDOFF CHECK ─────────────────────────────────────────────────
        # This is the FIRST thing we do before generating any response.
        # is_handoff_active() is an instant dict lookup (~0.1 microseconds).
        # If handoff is active, we return immediately without generating any text.
        # LiveKit will see an empty/closed stream and say nothing.
        if is_handoff_active(self._llm.thread_id):
            logger.info(f"[GraphStream] Handoff active. Muting AI response.")
            return   # Exit _run() immediately — no response generated

        # ... rest of the LLM logic (only runs if handoff is NOT active) ...

    finally:
        self._event_ch.close()  # Always close — even if we returned early above
```

---

## Trigger 1: Customer Requests a Human — `agent/graph_builder.py`

```python
# agent/graph_builder.py — router_node

def router_node(state: AgentState) -> dict:
    messages = state.get("messages", [])

    # ── FAST-PATH ESCALATION CHECK ────────────────────────────────────────────
    # Before any LLM classification, do a simple keyword check.
    # Why keyword check instead of classify_intent?
    # Speed. classify_intent calls the Groq LLM and takes ~300ms.
    # Detecting "I want a human" with string matching takes <1ms.
    # For such a clear, common request, the simpler approach wins.
    if messages:
        user_message = messages[-1].content.lower()
        if any(kw in user_message for kw in [
            "human", "representative", "agent", "supervisor",
            "manager", "handover", "transfer"
        ]):
            return {"current_flow": "escalation"}  # Route to escalate_node
```

```python
# agent/nodes.py — escalate_node (called when current_flow == "escalation")

def escalate_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Handles the escalation:
    1. Gets the session_id from LangGraph config (thread_id = session_id)
    2. Creates a support ticket in the backend (for human agents to see)
    3. Activates the handoff flag (AI goes silent)
    4. Returns a "transferring you now" message
    """
    # LangGraph passes config to nodes that declare a 'config' parameter.
    # config["configurable"]["thread_id"] = the session_id (which IS the thread_id).
    session_id = config.get("configurable", {}).get("thread_id")
    customer_id = state.get("customer_info", {}).get("id") if state.get("customer_verified") else None

    logger.info(f"[Escalation] Escalating call session: {session_id}")

    # ── CREATE SUPPORT TICKET ─────────────────────────────────────────────────
    # Before going silent, create a ticket so human agents can see
    # why this call was escalated.
    ticket_id = None
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/tickets",
            json={
                "customer_id": customer_id,
                "category": "Escalation",
                "description": "Customer requested human agent or failed identity verification."
            },
            timeout=5.0
        )
        if response.status_code == 200:
            ticket_id = response.json().get("ticket_id")
            logger.info(f"[Escalation] Ticket #{ticket_id} created.")
    except Exception as e:
        logger.error(f"[Escalation] Failed to create ticket: {e}")
        # Non-fatal — we still escalate even if ticketing fails

    # ── BUILD THE TRANSFER MESSAGE ────────────────────────────────────────────
    ticket_str = f" support ticket {ticket_id} has been created and" if ticket_id else ""
    msg = f"I am transferring you to a human agent now. A{ticket_str} representative will join this call shortly. Please hold."

    # ── ACTIVATE HANDOFF MODE ─────────────────────────────────────────────────
    # set_handoff_active(session_id, True) does two things:
    #   1. Sets _active_handoffs[session_id] = True in memory (instant)
    #   2. Updates call_sessions.status to "escalated" in Supabase (async)
    if session_id:
        set_handoff_active(session_id, True)
        logger.info(f"[Escalation] Session {session_id[:8]} placed in handoff.")

    # Return the message — this gets spoken by TTS, then AI goes silent
    return {
        "messages": [AIMessage(content=msg)],
        "current_flow": "escalation"
    }
```

---

## Trigger 2: Verification Fails 3 Times — `agent/nodes.py`

```python
# agent/nodes.py — verify_customer_node (excerpt)

def verify_customer_node(state: AgentState, config: RunnableConfig = None) -> dict:
    # ...
    attempts = state.get("verification_attempts", 0) + 1

    if attempts >= 3:
        # Three failed verification attempts → escalate for security
        session_id = config.get("configurable", {}).get("thread_id") if config else None
        if session_id:
            set_handoff_active(session_id, True)   # AI goes silent

        return {
            "messages": [AIMessage(
                content="I'm sorry, I'm still having trouble verifying your account. "
                        "Let me transfer you to a live support representative."
            )],
            "current_flow": "escalation",
            "verification_attempts": attempts
        }
```

---

## The Human Agent Joins the Room

The human agent uses the support dashboard (React app in `dashboard/`) to:
1. View active sessions from `GET /api/rooms/active-sessions`
2. Click "Join Call" → Dashboard calls `POST /api/token` with `role: "agent"`
3. Dashboard connects to the same LiveKit room as the customer

The agent's identity starts with `"agent_"` (e.g., `"agent_f3a8b2d1"`). This is important:

```python
# agent/main.py — on_track_published

@ctx.room.on("track_published")
def on_track_published(publication, participant):
    # When the human agent joins and publishes their audio,
    # we immediately unsubscribe so the AI agent doesn't hear them.
    # Without this, the AI would transcribe the human agent's voice
    # and try to respond to it, which would be very confusing.
    if participant.identity.startswith("agent_") or participant.identity.startswith("human_"):
        publication.set_subscribed(False)  # "Don't give me this audio track"
        logger.info(f"[Handoff] Unsubscribed from human agent track: {participant.identity}")
```

---

## The Human Sends a "Resume" Signal — `agent/main.py`

```python
# agent/main.py — on_data_received

@ctx.room.on("data_received")
def on_data_received(data_packet: rtc.DataPacket):
    """
    Receives custom data messages sent by any participant.
    The dashboard sends JSON messages like: {"action": "resume"} or {"action": "handoff"}

    data_packet.data is raw bytes (b'{"action": "resume"}').
    We decode it to a string, then parse as JSON.
    """
    try:
        payload_str = data_packet.data.decode("utf-8")   # bytes → string
        payload = json.loads(payload_str)                 # string → dict
        action = payload.get("action")

        if action == "resume":
            # Human clicked "Resume AI" in the dashboard
            logger.info("[Handoff] Received RESUME signal.")

            # Step 1: Turn off the handoff flag (AI can generate responses again)
            handoff.set_handoff_active(session_id, False)

            # Step 2: Have the AI greet the customer to signal it's back.
            # We need an async function for this because agent.say() is async.
            # But on_data_received is a regular (sync) function.
            # Solution: define an inner async function and schedule it with ensure_future().
            async def _speak_resume():
                await asyncio.sleep(0.3)   # Brief pause to let handoff flag propagate
                resume_text = "Welcome back! I'm back on the line. How can I help?"
                # Append to ChatContext so the graph knows the AI said this
                agent.chat_ctx.append(role="assistant", text=resume_text)
                # Actually speak it via TTS
                await agent.say(resume_text, allow_interruptions=True)
                logger.info("[Handoff] Resume greeting spoken.")

            asyncio.ensure_future(_speak_resume())

        elif action == "handoff":
            # Human clicked "Take Over" from the dashboard (manual override)
            logger.info("[Handoff] Received HANDOFF signal.")
            handoff.set_handoff_active(session_id, True)

    except Exception as e:
        logger.error(f"[Handoff] Error parsing data packet: {e}")
```

---

## Full Escalation Flow: End-to-End

```
Customer: "I need to speak to a real person"
       │
       ▼
on_user_speech_committed fires
       │
       ▼
LangGraphStream._run() is called
       ├─ is_handoff_active() → False (not yet escalated)
       ├─ Passes message through graph
       │
       ▼
entry_router → route_input → router_node
       ├─ Keyword check: "real person" → matches "representative"-adjacent keywords
       │  Actually: "person" isn't in the keywords. Let's check classify_intent.
       ├─ classify_intent("I need to speak to a real person") → Groq returns "escalate"
       └─ Returns {"current_flow": "escalation"}
       │
       ▼
route_flow_edge → "escalate"
       │
       ▼
escalate_node():
       ├─ POST /api/tickets {"category": "Escalation", ...} → ticket_id = 42
       ├─ set_handoff_active(session_id, True)
       │    ├─ _active_handoffs[session_id] = True  (in-memory, instant)
       │    └─ Supabase: UPDATE call_sessions SET status="escalated"
       └─ Returns AIMessage("I am transferring you now. Ticket 42 created. Please hold.")
       │
       ▼
LangGraph streams words → TTS speaks: "I am transferring you now..."
       │
       ▼
From this point: every future on_user_speech_committed call triggers:
       LangGraphStream._run()
           └─ is_handoff_active(session_id) → True → return immediately
           (AI is completely silent)
       │
       ▼
Human agent joins LiveKit room via dashboard:
       on_track_published fires → set_subscribed(False) (AI ignores human's audio)
       Human and customer talk directly.
       │
       ▼
Human clicks "Resume AI" in dashboard:
       Dashboard sends: room.localParticipant.publishData({"action": "resume"})
       │
       ▼
on_data_received fires:
       ├─ handoff.set_handoff_active(session_id, False)
       │    ├─ _active_handoffs[session_id] = False
       │    └─ Supabase: UPDATE call_sessions SET status="active"
       └─ asyncio.ensure_future(_speak_resume())
           └─ agent.say("Welcome back! I'm back on the line.")
       │
       ▼
Normal conversation resumes.
```

---

## Why Use an In-Memory Dict Instead of Checking Supabase?

This is a common architectural question. The answer is **latency**:

```
In-memory dict lookup:  ~0.1 microseconds (0.0001ms)
Supabase query:         ~100-300 milliseconds (100,000x slower)
```

Since `is_handoff_active()` is called before EVERY single LLM response, using Supabase
would add 100-300ms to every voice turn. That would make the voice agent feel sluggish.

The in-memory approach means the handoff state only lives in the worker process's RAM.
If the process restarts, it resets to `False` (not in handoff). But since worker crashes
mean the LiveKit room is also gone, this doesn't create real inconsistency.

---

*Next up → [11_WALKTHROUGH_config.md](./11_WALKTHROUGH_config.md)*
