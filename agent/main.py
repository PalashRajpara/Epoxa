"""
agent/main.py  (Phase 3 — Production Features)
===============================================
This is the main LiveKit agent file. Phase 3 adds:

  1. CALL SESSION TRACKING  — creates a database record when a call starts
  2. TRANSCRIPT CAPTURE     — saves every word said (user + agent) to the database
  3. LATENCY LOGGING        — measures how long STT, LLM, and TTS each take
  4. ROOM EVENT LISTENERS   — detects when participants join, leave, or disconnect
  5. RECONNECTION HANDLING  — gracefully recovers if a customer's connection drops
  6. SESSION TIMEOUT        — ends the call if no activity for too long
  7. CALL SUMMARY           — generates a 2-3 sentence LLM summary at the end
  8. ERROR HANDLING         — all failures are caught so the agent never crashes

HOW IT ALL FITS TOGETHER:
  - When a call starts: create a call_sessions row in Supabase
  - During the call: append each utterance to call_transcripts
  - During the call: log STT/LLM/TTS timing to latency_logs
  - When the call ends: generate summary, update call_sessions with status + summary

NOTE ON DATABASE:
  - Supabase calls are fire-and-forget (we don't wait for them to finish)
  - If Supabase is down, the call continues normally — we just lose the logging
  - This is "graceful degradation" — the core feature (voice AI) never breaks
"""

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure an event loop is set for Python 3.12+ compatibility,
# especially inside spawned worker subprocesses on macOS.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# =============================================================================
# PATH SETUP
# =============================================================================
# The agent has its own folder, but we want to use the shared database/utils
# from the backend folder. We add the backend directory to the Python path
# so imports like "from database.connection import ..." work correctly.
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Also load environment variables from the root .env file
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"), override=True)

# =============================================================================
# LOGGING SETUP (Phase 3)
# =============================================================================
# Set up structured logging BEFORE importing anything else.
# This ensures all log messages go to both the terminal and logs/app.log.
from utils import setup_logging, get_logger
setup_logging(level="INFO")
logger = get_logger("agent.main")

# =============================================================================
# LIVEKIT IMPORTS
# =============================================================================
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent

# rtc = Real-Time Communication. This gives us access to Room and Participant events.
from livekit import rtc

from livekit.plugins import silero, deepgram

# =============================================================================
# PROJECT IMPORTS
# =============================================================================
from config import settings
from graph_builder import compiled_graph, LangGraphLLM

# Phase 3: Database helpers (Supabase)
from database import (
    create_call_session,
    complete_call_session,
    save_transcript_entry,
    get_full_transcript,
    get_customer_call_history,
)

# Phase 3: Latency tracker
from utils import LatencyTracker

# Phase 4: Handoff manager
import handoff

# Pre-load Silero VAD plugin globally on startup
logger.info("Pre-loading Silero VAD plugin...")
VAD_PLUGIN = silero.VAD.load()

# Pre-warm ChromaDB SentenceTransformer embedding model.
# Without this, the model loads on the FIRST call (causing a 6-9 second delay).
# Running a dummy query here forces it to load into memory at startup instead.
logger.info("Pre-warming ChromaDB SentenceTransformer embedding model...")
try:
    from chroma_client import query_faq as _warmup_query
    _warmup_query("warmup", n_results=1)
    logger.info("ChromaDB embedding model pre-warmed successfully.")
except Exception as _warmup_err:
    logger.warning(f"ChromaDB pre-warm failed (non-fatal): {_warmup_err}")

# =============================================================================
# CONFIGURATION
# =============================================================================

# How many minutes of silence before we auto-end the call.
# If the customer doesn't speak for this long, we assume they've left.
SESSION_TIMEOUT_MINUTES = 1

# How many times to attempt reconnecting if the connection drops.
MAX_RECONNECT_ATTEMPTS = 3

# How many seconds to wait between reconnection attempts.
RECONNECT_WAIT_SECONDS = 2

# Validate the config before startup (checks all required env vars are set)
settings.validate_config()
logger.info("Agent configuration validated successfully")


# =============================================================================
# CALL SUMMARY GENERATOR
# =============================================================================

async def generate_call_summary(session_id: str) -> str:
    """
    Fetches the full conversation transcript and asks Groq to summarize it.

    This runs at the END of a call. It:
    1. Fetches all transcript lines for this session from Supabase
    2. Formats them into a readable conversation
    3. Sends it to Groq LLM with a summarization prompt
    4. Returns the 2-3 sentence summary

    Args:
        session_id: The UUID of the call to summarize

    Returns:
        A 2-3 sentence summary string, or "[Summary unavailable]" if it fails.
    """
    logger.info(f"[Summary] Generating call summary for session {session_id[:8]}...")

    # Step 1: Get all transcript entries for this call
    transcript_entries = get_full_transcript(session_id)

    if not transcript_entries:
        logger.warning(f"[Summary] No transcript found for session {session_id[:8]}, skipping summary")
        return "[No transcript available — call may have been too short]"

    # Step 2: Format the transcript as a readable conversation
    # Example:
    #   User: I want to book an appointment
    #   Agent: I'd be happy to help. What date works for you?
    conversation_text = "\n".join([
        f"{entry['role'].capitalize()}: {entry['content']}"
        for entry in transcript_entries
    ])

    logger.info(f"[Summary] Transcript has {len(transcript_entries)} entries. Sending to Groq...")

    # Step 3: Call Groq LLM to generate the summary
    try:
        # We use the same Groq setup as the graph builder (ChatOpenAI pointing to Groq's API)
        from langchain_openai import ChatOpenAI
        groq_llm = ChatOpenAI(
            model="llama-3.1-8b-instant",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )

        # This is the prompt we send to Groq.
        # We tell it exactly what we want: a brief, structured summary.
        summary_prompt = (
            "You are a customer support call analyst. "
            "Read the following support call transcript and write a brief 2-3 sentence summary. "
            "Include: (1) what the customer needed help with, (2) what actions were taken, "
            "and (3) the final outcome. Be concise and factual.\n\n"
            f"TRANSCRIPT:\n{conversation_text}\n\n"
            "SUMMARY:"
        )

        response = groq_llm.invoke(summary_prompt)
        summary = response.content.strip()
        logger.info(f"[Summary] Summary generated successfully: {summary[:80]}...")
        return summary

    except Exception as e:
        # If the LLM call fails, don't crash — just return a placeholder
        logger.error(f"[Summary] Failed to generate summary: {e}")
        return "[Summary unavailable — LLM error during call end]"


# =============================================================================
# CALL CLEANUP FUNCTION
# =============================================================================

async def end_call_gracefully(
    session_id: str,
    call_start_time: datetime,
    status: str,
    disconnect_reason: str = None,
) -> None:
    """
    Called when a call ends for ANY reason (normal hangup, dropout, timeout, error).
    This function:
    1. Calculates how long the call lasted
    2. Generates an LLM summary of the conversation
    3. Updates the call_sessions record in Supabase with all the final data

    Args:
        session_id: The UUID of the call
        call_start_time: When the call started (datetime object)
        status: "completed", "dropped", "timeout", or "error"
        disconnect_reason: Optional human-readable reason for the disconnect
    """
    logger.info(f"[Cleanup] Ending call session {session_id[:8]}... status={status}")

    # Calculate how long the call lasted in seconds
    call_end_time = datetime.now(timezone.utc)
    duration_seconds = int((call_end_time - call_start_time).total_seconds())
    logger.info(f"[Cleanup] Call duration: {duration_seconds} seconds")

    # Generate the LLM summary (this makes an API call to Groq)
    summary = await generate_call_summary(session_id)

    # Update the Supabase call_sessions record with all the final information
    complete_call_session(
        session_id=session_id,
        status=status,
        duration_seconds=duration_seconds,
        summary=summary,
        disconnect_reason=disconnect_reason,
    )

    logger.info(f"[Cleanup] Call session {session_id[:8]}... finalized in Supabase")


# =============================================================================
# MAIN AGENT ENTRYPOINT
# =============================================================================

async def entrypoint(ctx: JobContext):
    """
    Entrypoint function — called by LiveKit when a participant joins a room
    and triggers a dispatch event for this agent.

    This is the main function that sets up the entire call:
    - Creates the database session record
    - Sets up the voice pipeline (STT → LLM → TTS)
    - Attaches all event listeners (transcript, latency, room events)
    - Handles reconnection, timeout, and cleanup
    """
    logger.info(f"[Agent] New job received for room: {ctx.room.name}")

    # =========================================================================
    # PHASE 3: SESSION SETUP
    # =========================================================================

    # Generate a unique ID for this call session.
    # uuid.uuid4() creates a random UUID like "550e8400-e29b-41d4-a716-446655440000"
    # str() converts it to a string so we can store it
    session_id = str(uuid.uuid4())

    # Record when the call started. We'll use this later to calculate duration.
    call_start_time = datetime.now(timezone.utc)

    # Track how many messages have been exchanged (for ordering the transcript)
    # We use a list with one item so we can modify it inside nested functions.
    # (In Python, you can't do "count += 1" inside a closure unless the variable
    # is mutable like a list — this is a common beginner-friendly pattern.)
    message_sequence = [0]

    # Track whether any reconnection is happening
    reconnect_attempts = [0]

    # Track the last time the user spoke (used for session timeout detection)
    last_activity_time = [datetime.now(timezone.utc)]

    # Create the initial call_sessions record in Supabase.
    # NOTE: We do NOT pass room_sid here because ctx.room.sid is an async
    # property that must be awaited — we can only do that after ctx.connect().
    # We update room_sid separately after connecting (see below).
    session_created = create_call_session(
        session_id=session_id,
        room_name=ctx.room.name,
        room_sid=None,             # Will be filled in after await ctx.connect()
        participant_name=None,     # Will be filled in from participant_connected event
    )
    if session_created:
        logger.info(f"[Agent] Call session created in Supabase: {session_id}")
    else:
        logger.warning(f"[Agent] Could not create call session in Supabase — calls will still work but won't be saved")

    # Create a latency tracker for this session
    # This will time each STT/LLM/TTS step
    latency_tracker = LatencyTracker(session_id=session_id)

    # =========================================================================
    # PIPELINE SETUP
    # =========================================================================

    # Establish connection to the room (audio only to keep traffic clean)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("[Agent] Connected to room. Waiting for participants...")

    # Get the room SID and update Supabase asynchronously in a background task.
    # We do NOT await this in the main task, because ctx.room.sid is an async property
    # that blocks until the room is fully set up. Awaiting it here delays agent startup
    # and greeting by 30-40 seconds, causing silent call failure.
    async def update_room_sid_background():
        try:
            # Await the SID asynchronously in the background
            sid = await ctx.room.sid
            logger.info(f"[DB] Retrieved Room SID in background: {sid}")
            
            # Save it to database (SQLite + Supabase)
            from database import update_call_session_room_sid
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: update_call_session_room_sid(session_id, sid)
            )
            logger.info(f"[DB] Asynchronously updated room_sid to: {sid}")
        except Exception as e:
            logger.warning(f"[Agent] Could not retrieve or save room_sid in background: {e}")

    # Start the background task immediately (non-blocking)
    asyncio.create_task(update_room_sid_background())

    # System prompt — tells the AI how to behave
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are Epixa, a helpful customer support agent for Epoxcel"
            "Keep your responses concise, friendly, and conversational since this is a voice-based interaction. "
            "Avoid listing bullet points in your speech; speak in natural, complete sentences."
        )
    )

    # Speech-to-Text (STT) powered by Deepgram
    # Deepgram listens to the customer's voice and converts it to text
    stt_plugin = deepgram.STT(
        api_key=settings.DEEPGRAM_STT_API_KEY
    )

    # LLM powered by LangGraph (our custom stateful conversation graph)
    # Use session_id directly as the thread_id because it is a unique string UUID
    # ready immediately. Do not use ctx.room.sid here to avoid passing a coroutine object.
    thread_id = session_id
    llm_plugin = LangGraphLLM(
        graph=compiled_graph,
        thread_id=thread_id
    )

    # Text-to-Speech (TTS) powered by Deepgram
    # Deepgram takes the AI's text response and speaks it out loud
    tts_plugin = deepgram.TTS(
        api_key=settings.DEEPGRAM_TTS_API_KEY,
        model="aura-asteria-en",   # Natural female English voice
        use_streaming=True          # Streaming = faster first audio chunk
    )

    # Voice Activity Detection (VAD) by Silero
    # VAD detects when the user starts/stops speaking so we know when to listen
    vad_plugin = VAD_PLUGIN

    # Assemble the VoicePipelineAgent — this orchestrates the full STT → LLM → TTS flow
    agent = VoicePipelineAgent(
        vad=vad_plugin,
        stt=stt_plugin,
        llm=llm_plugin,
        tts=tts_plugin,
        chat_ctx=initial_ctx,
        preemptive_synthesis=True,
        min_endpointing_delay=0.5
    )

    # =========================================================================
    # EVENT LISTENERS — TRANSCRIPT CAPTURE (Phase 3)
    # =========================================================================
    # LiveKit fires events when a complete utterance finishes.
    # "user_speech_committed" fires after the customer finishes a full sentence.
    # "agent_speech_committed" fires after the agent finishes speaking.
    # We hook into these to save the transcript line-by-line.

    @agent.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage):
        """
        Called every time the user finishes speaking a complete utterance.
        'committed' means the VAD has confirmed they stopped talking.

        We save this to call_transcripts in Supabase.
        """
        # Get the text content of what was said
        text = msg.content if isinstance(msg.content, str) else ""
        if not text.strip():
            return  # Skip empty messages

        # Update the sequence counter for ordering
        message_sequence[0] += 1

        # Update last activity time (resets session timeout countdown)
        last_activity_time[0] = datetime.now(timezone.utc)

        logger.info(f"[Transcript] USER (#{message_sequence[0]}): {text[:80]}")

        # Save to Supabase (in a background task so it doesn't block the call)
        # asyncio.ensure_future() schedules the coroutine to run without waiting for it
        asyncio.ensure_future(
            _save_transcript_async(session_id, "user", text, message_sequence[0])
        )

    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        """
        Called every time the agent finishes speaking a complete utterance.

        We save this to call_transcripts in Supabase.
        """
        text = msg.content if isinstance(msg.content, str) else ""
        if not text.strip():
            return

        message_sequence[0] += 1
        logger.info(f"[Transcript] AGENT (#{message_sequence[0]}): {text[:80]}")

        asyncio.ensure_future(
            _save_transcript_async(session_id, "agent", text, message_sequence[0])
        )

    # =========================================================================
    # EVENT LISTENERS — LATENCY TRACKING (Phase 3)
    # =========================================================================
    # These events fire at the start and end of each pipeline stage.
    # We use them to precisely time how long each step takes.

    @agent.on("user_started_speaking")
    def on_user_started_speaking():
        """User began speaking — start timing STT (we're about to transcribe their voice)."""
        logger.info("🎙️ [Event] User started speaking...")
        # Reset the tracker for a new turn
        latency_tracker.reset()
        # Start the STT timer
        latency_tracker.start("stt")

    @agent.on("user_stopped_speaking")
    def on_user_stopped_speaking():
        """User stopped speaking — STT is processing the audio now."""
        logger.info("🎙️ [Event] User stopped speaking (processing...)")
        # STT step ends (we now have the transcribed text)
        latency_tracker.end("stt")
        # Immediately start timing the LLM step
        latency_tracker.start("llm")

    @agent.on("agent_started_speaking")
    def on_agent_started_speaking():
        """
        Agent began speaking — LLM is done (it generated the reply),
        and TTS has started converting it to audio.
        """
        logger.info("🤖 [Event] Agent started speaking...")
        # LLM step ends (the response was generated)
        latency_tracker.end("llm")
        # Start timing TTS (audio is being synthesized and streamed)
        latency_tracker.start("tts")

    @agent.on("agent_stopped_speaking")
    def on_agent_stopped_speaking():
        """Agent finished speaking — TTS is complete for this turn."""
        logger.info("🤖 [Event] Agent stopped speaking.")
        # TTS step ends
        latency_tracker.end("tts")
        # Print a one-line summary showing ALL timings for this turn
        latency_tracker.print_summary()

    # =========================================================================
    # ROOM EVENT LISTENERS (Phase 3)
    # =========================================================================
    # ctx.room gives us access to the LiveKit Room object.
    # We can listen for events like participants joining or leaving.

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        """
        Called when ANY participant joins the room.
        In our setup, this will be the customer (the agent is already in the room).

        We log the join and update the call_sessions record with the participant's name.
        """
        logger.info(f"[Room Event] Participant JOINED: {participant.identity} | Name: {participant.name}")

        # Update last activity time — someone just joined!
        last_activity_time[0] = datetime.now(timezone.utc)

        # Update the Supabase session with the participant's name (we didn't know it at call start)
        # We do this in a background task
        asyncio.ensure_future(
            _update_session_participant_async(session_id, participant.name or participant.identity)
        )

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        """
        Called when a participant LEAVES the room.
        This can happen because:
        - They clicked "End Call" (normal)
        - Their network dropped (reconnection will be attempted)
        - Their browser closed

        IMPORTANT: This does NOT immediately end the call — the room stays open
        for a grace period in case they reconnect. We end the call in the main loop
        when the room actually closes or times out.
        """
        logger.info(f"[Room Event] Participant DISCONNECTED: {participant.identity}")
        logger.info("[Room Event] Waiting to see if they reconnect (room stays open briefly)...")

    # =========================================================================
    # PHASE 4: MULTI-PARTICIPANT / HANDOFF EVENT LISTENERS
    # =========================================================================
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        """
        Triggered when a participant publishes a new track.
        If the track is published by a human agent, we immediately unsubscribe from it
        so the AI agent never hears or responds to the human agent.
        """
        if participant.identity.startswith("agent_") or participant.identity.startswith("human_"):
            logger.info(f"[Handoff] Ignoring published audio track from human agent: {participant.identity}")
            publication.set_subscribed(False)

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        """
        Triggered when our agent successfully subscribes to a track.
        Double-check and unsubscribe if it is from a human agent.
        """
        if participant.identity.startswith("agent_") or participant.identity.startswith("human_"):
            logger.info(f"[Handoff] Unsubscribing from human agent track: {participant.identity}")
            publication.set_subscribed(False)

    @ctx.room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        """
        Triggered when any participant sends a custom data message over the LiveKit room.
        This is how the human agent support dashboard signals actions like 'resume' to the AI.
        """
        try:
            # Decode the raw bytes payload
            payload_str = data_packet.data.decode("utf-8")
            payload = json.loads(payload_str)
            action = payload.get("action")

            if action == "resume":
                logger.info(f"[Handoff] Received RESUME signal from {data_packet.participant.identity if data_packet.participant else 'unknown'}")

                # 1. Turn off handoff mode so the AI starts responding again
                handoff.set_handoff_active(session_id, False)

                # 2. Speak the resume greeting.
                # We use an inner async function + asyncio.ensure_future() because
                # on_data_received is a plain sync function — asyncio.create_task() is
                # unreliable here and can silently drop the task.
                # ensure_future() safely schedules a coroutine on the running event loop.
                # The small sleep gives the handoff flag a moment to fully propagate
                # before the agent tries to generate a response.
                async def _speak_resume():
                    await asyncio.sleep(0.3)  # Brief pause to let handoff flag clear
                    resume_text = "Welcome back! I'm back on the line. How can I help you resolve the rest of your issue?"
                    agent.chat_ctx.append(role="assistant", text=resume_text)
                    await agent.say(resume_text, allow_interruptions=True)
                    logger.info("[Handoff] Resume greeting spoken successfully.")

                asyncio.ensure_future(_speak_resume())

            elif action == "handoff":
                logger.info(f"[Handoff] Received Handoff trigger from {data_packet.participant.identity if data_packet.participant else 'unknown'}")
                # Set handoff mode to active — the AI will stay silent until a resume signal arrives
                handoff.set_handoff_active(session_id, True)

        except Exception as e:
            logger.error(f"[Handoff] Error parsing received data packet: {e}")

    @ctx.room.on("reconnecting")
    def on_room_reconnecting():
        """
        Called when the AGENT's connection to the LiveKit server is unstable
        and LiveKit is attempting to reconnect automatically.

        Note: This is the AGENT's reconnection, not the customer's.
        LiveKit handles this automatically, we just log it.
        """
        reconnect_attempts[0] += 1
        logger.warning(
            f"[Room Event] Agent connection unstable — reconnecting... "
            f"(attempt {reconnect_attempts[0]}/{MAX_RECONNECT_ATTEMPTS})"
        )

    @ctx.room.on("reconnected")
    def on_room_reconnected():
        """
        Called when the agent successfully reconnects after a drop.
        We reset the reconnect counter since we're back online.
        """
        reconnect_attempts[0] = 0
        logger.info("[Room Event] Agent reconnected successfully ✓")

    @ctx.room.on("disconnected")
    def on_room_disconnected(reason: rtc.DisconnectReason = None):
        """
        Called when the room itself fully disconnects (both agent and customer).
        This is the final event — after this, the call is truly over.
        We use reason to label the disconnect in Supabase.
        """
        reason_str = str(reason) if reason else "unknown"
        logger.info(f"[Room Event] Room DISCONNECTED. Reason: {reason_str}")

    # =========================================================================
    # START THE AGENT
    # =========================================================================

    # Start the agent — this begins listening in the room
    agent.start(ctx.room)

    # Wait briefly for connection channels to stabilize, then greet the customer
    await asyncio.sleep(0.3)

    greeting_text = "Hello! Welcome to Epoxcel. My name is Epixa. How can I help you today?"
    try:
        from langchain_core.messages import AIMessage
        config = {"configurable": {"thread_id": session_id}}
        await compiled_graph.aupdate_state(
            config,
            {
                "messages": [AIMessage(content=greeting_text)],
                "current_flow": "greeting"
            }
        )
    except Exception as e:
        logger.error(f"[Agent] Failed to initialize LangGraph greeting state: {e}")

    initial_ctx.append(role="assistant", text=greeting_text)
    await agent.say(greeting_text, allow_interruptions=True)

    logger.info("[Agent] Greeting sent. Entering main call loop.")



    # =========================================================================
    # MAIN CALL LOOP (with timeout detection)
    # =========================================================================
    # We stay in this loop until the call ends.
    # Every 30 seconds, we check if the customer has been silent too long.

    call_ended = False
    timeout_seconds = SESSION_TIMEOUT_MINUTES * 60  # Convert minutes to seconds
    check_interval = 30  # Check for timeout every 30 seconds

    try:
        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            # Wait 30 seconds before checking again
            await asyncio.sleep(check_interval)

            # Check if the customer has been silent for too long
            silence_duration = (datetime.now(timezone.utc) - last_activity_time[0]).total_seconds()

            if silence_duration > timeout_seconds:
                # Customer has been silent for SESSION_TIMEOUT_MINUTES minutes
                logger.warning(
                    f"[Timeout] No activity for {silence_duration:.0f}s "
                    f"(limit: {timeout_seconds}s). Ending session."
                )
                # Politely inform the customer before disconnecting
                await agent.say(
                    "It seems you may have stepped away. I'll end our session now. "
                    "Feel free to call back anytime. Goodbye!",
                    allow_interruptions=False
                )
                await asyncio.sleep(3)  # Give TTS time to finish

                # End the call gracefully
                await end_call_gracefully(
                    session_id=session_id,
                    call_start_time=call_start_time,
                    status="timeout",
                    disconnect_reason=f"Session timed out after {SESSION_TIMEOUT_MINUTES} minutes of inactivity",
                )
                call_ended = True
                break  # Exit the loop

        # If the loop ended because the room disconnected (not timeout),
        # finalize the call session if we haven't already
        if not call_ended:
            logger.info("[Agent] Room connection ended. Finalizing call session...")
            await end_call_gracefully(
                session_id=session_id,
                call_start_time=call_start_time,
                status="completed",
                disconnect_reason="participant_disconnected",
            )

    except Exception as e:
        # Something unexpected happened during the call loop
        logger.error(f"[Agent] Unexpected error in call loop: {e}", exc_info=True)

        # Still try to finalize the session even if there was an error
        if not call_ended:
            await end_call_gracefully(
                session_id=session_id,
                call_start_time=call_start_time,
                status="error",
                disconnect_reason=f"Unexpected error: {str(e)}",
            )

    logger.info(f"[Agent] Session {session_id[:8]}... fully completed.")


# =============================================================================
# ASYNC HELPER FUNCTIONS
# =============================================================================
# These are small async wrappers around synchronous database calls.
# We run them as background tasks so they don't block the voice pipeline.

async def _save_transcript_async(session_id: str, role: str, content: str, sequence: int) -> None:
    """
    Background task to save a transcript entry.
    Runs asynchronously so it doesn't delay the agent's voice response.
    """
    try:
        # Run the synchronous DB call in an executor so it doesn't block the event loop
        # asyncio.get_event_loop().run_in_executor() moves a blocking call to a thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,  # None = use the default thread pool
            lambda: save_transcript_entry(session_id, role, content, sequence)
        )
    except Exception as e:
        # Never crash the call because of a logging failure
        logger.error(f"[Transcript] Failed to save entry async: {e}")


async def _update_session_participant_async(session_id: str, participant_name: str) -> None:
    """
    Background task to update the participant_name in call_sessions.
    We don't know the name when the call starts — we learn it when they join.
    """
    try:
        from database import update_call_session_participant
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: update_call_session_participant(session_id, participant_name)
        )
        logger.info(f"[DB] Updated participant name to: {participant_name}")
    except Exception as e:
        logger.error(f"[DB] Failed to update participant name: {e}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Start the LiveKit CLI app worker.
    # In development mode, run with: python main.py dev
    # In production, run with: python main.py start
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            initialize_process_timeout=60.0  # 60 seconds to start up before failing
        )
    )
