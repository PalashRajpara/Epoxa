"""Epoxa LiveKit Voice Agent Worker.

Production refactor:
- Consumes epoxa_core services directly.
- Off-the-hot-path persistence queue for transcripts, latencies, and session updates.
- Authoritative handoff state coordination.
- Strict preservation of audio isolation, non-blocking room.sid, and pipeline timing invariants.
"""

import asyncio
from datetime import datetime, timezone
import json
import signal
from typing import Optional
import structlog

from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, silero

from epoxa_agent.graph import LangGraphLLM, build_graph
from epoxa_agent.handoff import (
    is_ai_silenced,
    refresh_authoritative_handoff_state,
    set_authoritative_handoff_state,
    update_local_handoff_cache,
)
from epoxa_agent.latency import LatencyTracker
from epoxa_agent.persistence import AsyncPersistenceWorker
from epoxa_core.logging import setup_logging
from epoxa_core.settings import get_settings

setup_logging()
logger = structlog.get_logger("epoxa_agent.main")
settings = get_settings()

# Initialize global persistence worker
persistence_worker = AsyncPersistenceWorker()

# Pre-load Silero VAD plugin globally on startup
logger.info("preloading_silero_vad")
VAD_PLUGIN = silero.VAD.load()

# Pre-warm compiled conversation graph
logger.info("compiling_langgraph_statemachine")
compiled_graph = build_graph()

async def generate_call_summary(session_id: str, transcript_lines: list[str]) -> str:
    """Generate concise 2-3 sentence LLM summary at call completion."""
    if not transcript_lines:
        return "Call ended without spoken conversation."
    full_text = "\n".join(transcript_lines)
    prompt = (
        "Summarize the following customer support phone call in 2-3 concise sentences. "
        "Highlight the customer's request, actions taken, and the resolution status.\n\n"
        f"Transcript:\n{full_text}\n\nSummary:"
    )
    try:
        from epoxa_agent.nodes import get_agent_container
        container = get_agent_container()
        res = container.llm.invoke(prompt)
        return str(res.content).strip()
    except Exception as e:
        logger.warning("call_summary_generation_failed", session_id=session_id, error=str(e))
        return "Summary generation unavailable."

async def entrypoint(ctx: JobContext) -> None:
    """LiveKit agent worker entrypoint called when a call dispatch triggers."""
    session_id = ctx.room.name  # Server sets room.name to session_id (or unguessable room string)
    logger.info("agent_dispatch_received", room=ctx.room.name, session_id=session_id)

    persistence_worker.start()

    call_start_time = datetime.now(timezone.utc)
    message_sequence = [0]
    last_activity_time = [datetime.now(timezone.utc)]
    transcript_accumulator: list[str] = []

    # Refresh and sync authoritative handoff state
    initial_handoff = await refresh_authoritative_handoff_state(session_id)
    logger.info("initial_handoff_state_loaded", session_id=session_id, state=initial_handoff)

    # Latency tracking setup
    latency_tracker = LatencyTracker(
        session_id=session_id,
        on_turn_complete=lambda durations: persistence_worker.enqueue_latency(
            session_id=session_id,
            turn_index=latency_tracker.turn_index,
            durations=durations,
        ),
    )

    # Establish room connection (Audio only)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("agent_connected_to_room", room=ctx.room.name)

    # INVARIANT 1: Non-blocking room.sid retrieval
    async def update_room_sid_background() -> None:
        try:
            sid = await ctx.room.sid
            logger.info("retrieved_room_sid_background", sid=sid)
            persistence_worker.enqueue_session_update(session_id, {"livekit_room_sid": sid})
        except Exception as e:
            logger.warning("failed_to_retrieve_room_sid_background", error=str(e))

    asyncio.create_task(update_room_sid_background(), name="fetch_room_sid")

    # System chat context
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a helpful and friendly voice customer support agent for Voice AI Agent. "
            "Keep your responses concise, friendly, and conversational since this is a voice-based interaction. "
            "Avoid listing bullet points in your speech; speak in natural, complete sentences."
        ),
    )

    # STT Plugin (Deepgram)
    stt_plugin = deepgram.STT(api_key=settings.DEEPGRAM_STT_API_KEY.get_secret_value())

    # TTS Plugin (Deepgram)
    tts_plugin = deepgram.TTS(
        api_key=settings.DEEPGRAM_TTS_API_KEY.get_secret_value(),
        model="aura-asteria-en",
        use_streaming=True,
    )

    # LLM Plugin (LangGraph adapter)
    llm_plugin = LangGraphLLM(graph=compiled_graph, thread_id=session_id)

    # INVARIANT 6: Exact voice pipeline timing configurations
    agent = VoicePipelineAgent(
        vad=VAD_PLUGIN,
        stt=stt_plugin,
        llm=llm_plugin,
        tts=tts_plugin,
        chat_ctx=initial_ctx,
        interrupt_speech_duration=0.7,
        interrupt_min_words=2,
        min_endpointing_delay=0.6,
        preemptive_synthesis=False,
    )

    # =========================================================================
    # EVENT LISTENERS: TRANSCRIPTS & LATENCIES
    # =========================================================================
    @agent.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage) -> None:
        text = (
            msg.content
            if isinstance(msg.content, str)
            else " ".join([str(c) for c in msg.content])
            if isinstance(msg.content, list)
            else str(msg.content or "")
        )
        if not text.strip():
            return

        message_sequence[0] += 1
        last_activity_time[0] = datetime.now(timezone.utc)
        transcript_accumulator.append(f"Customer: {text}")

        # Enqueue off the audio hot path
        persistence_worker.enqueue_transcript(
            session_id=session_id,
            role="user",
            content=text,
            sequence=message_sequence[0],
        )

    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage) -> None:
        text = (
            msg.content
            if isinstance(msg.content, str)
            else " ".join([str(c) for c in msg.content])
            if isinstance(msg.content, list)
            else str(msg.content or "")
        )
        if not text.strip():
            return

        message_sequence[0] += 1
        transcript_accumulator.append(f"Agent: {text}")

        persistence_worker.enqueue_transcript(
            session_id=session_id,
            role="agent",
            content=text,
            sequence=message_sequence[0],
        )

    @agent.on("user_started_speaking")
    def on_user_started_speaking() -> None:
        latency_tracker.reset()
        latency_tracker.start("stt")

    @agent.on("user_stopped_speaking")
    def on_user_stopped_speaking() -> None:
        latency_tracker.end("stt")
        latency_tracker.start("llm")

    @agent.on("agent_started_speaking")
    def on_agent_started_speaking() -> None:
        latency_tracker.end("llm")
        latency_tracker.start("tts")

    @agent.on("agent_stopped_speaking")
    def on_agent_stopped_speaking() -> None:
        latency_tracker.end("tts")
        latency_tracker.record_e2e()

    # =========================================================================
    # INVARIANT 2: MULTI-PARTICIPANT AUDIO TRACK ISOLATION
    # =========================================================================
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant) -> None:
        if participant.identity.startswith("agent_") or participant.identity.startswith("human_"):
            logger.info("audio_isolation_unsubscribe_published", participant=participant.identity)
            publication.set_subscribed(False)

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant) -> None:
        if participant.identity.startswith("agent_") or participant.identity.startswith("human_"):
            logger.info("audio_isolation_unsubscribe_subscribed", participant=participant.identity)
            publication.set_subscribed(False)

    # Server-Authoritative LiveKit Data Messages (Handoff / Resume)
    @ctx.room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket) -> None:
        try:
            payload = json.loads(data_packet.data.decode("utf-8"))
            action = payload.get("action")
            if action == "resume":
                logger.info("received_handoff_resume_signal", session_id=session_id)
                update_local_handoff_cache(session_id, "ai")

                async def _speak_resume() -> None:
                    await asyncio.sleep(0.3)
                    resume_text = "Welcome back! I'm back on the line. How can I help you resolve the rest of your issue?"
                    agent.chat_ctx.append(role="assistant", text=resume_text)
                    await agent.say(resume_text, allow_interruptions=True)

                asyncio.ensure_future(_speak_resume())

            elif action in ("takeover", "handoff"):
                logger.info("received_handoff_takeover_signal", session_id=session_id)
                update_local_handoff_cache(session_id, "human_active")

        except Exception as e:
            logger.error("error_parsing_room_data_packet", error=str(e))

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant) -> None:
        logger.info("participant_joined_room", identity=participant.identity, name=participant.name)
        last_activity_time[0] = datetime.now(timezone.utc)
        name = participant.name or participant.identity
        persistence_worker.enqueue_session_update(session_id, {"participant_name": name})

    # Start the Voice Agent
    agent.start(ctx.room)
    await asyncio.sleep(0.3)

    # Greet the caller
    greeting_text = "Hello! Welcome to Voice AI Agent. How can I help you today?"
    initial_ctx.append(role="assistant", text=greeting_text)
    await agent.say(greeting_text, allow_interruptions=True)

    # Main monitoring loop (Session Timeout detection & Max Call Duration)
    timeout_seconds = settings.CALL_TIMEOUT_SECONDS
    max_duration_seconds = settings.MAX_CALL_DURATION_MINUTES * 60
    end_reason = "completed"

    try:
        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(15)

            now = datetime.now(timezone.utc)
            total_duration = (now - call_start_time).total_seconds()
            silence_duration = (now - last_activity_time[0]).total_seconds()

            # Hard max call length protection (D7)
            if total_duration > max_duration_seconds:
                logger.info("max_call_duration_exceeded", session_id=session_id, duration=total_duration)
                await agent.say(
                    "Our call has reached the maximum allowed duration. Thank you for contacting Voice AI Agent. Goodbye!",
                    allow_interruptions=False,
                )
                await asyncio.sleep(3)
                end_reason = "timeout"
                break

            # Inactivity timeout
            if silence_duration > timeout_seconds:
                logger.info("call_inactivity_timeout", session_id=session_id, silence=silence_duration)
                await agent.say(
                    "It seems you may have stepped away. I will conclude our call now. Goodbye!",
                    allow_interruptions=False,
                )
                await asyncio.sleep(3)
                end_reason = "timeout"
                break

    except Exception as e:
        logger.error("error_in_main_agent_loop", session_id=session_id, error=str(e))
        end_reason = "error"
    finally:
        now = datetime.now(timezone.utc)
        duration = max(0, int((now - call_start_time).total_seconds()))
        summary = await generate_call_summary(session_id, transcript_accumulator)

        persistence_worker.enqueue_session_update(
            session_id,
            {
                "status": "completed" if end_reason == "completed" else end_reason,
                "ended_at": now,
                "duration_seconds": duration,
                "end_reason": end_reason,
                "summary": summary,
            },
        )
        logger.info("call_session_finalized", session_id=session_id, duration=duration, reason=end_reason)

def main() -> None:
    """CLI launcher for LiveKit worker."""
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            initialize_process_timeout=60.0,
        )
    )

if __name__ == "__main__":
    main()
