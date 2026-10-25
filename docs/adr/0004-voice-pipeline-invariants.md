# ADR 0004: Voice Pipeline Invariants and Latency Tuning

## Status
Accepted

## Context
Voice AI systems are hypersensitive to latency, audio pipeline scheduling, and WebRTC participant routing. Five critical invariants were documented in Section 14 of `PROJECT_CONTEXT.md` that must never regress:
1. Non-blocking `room.sid` retrieval.
2. Multi-participant audio track isolation.
3. Explicit DOM audio element attachment.
4. Word-boundary regex for escalation routing.
5. Voice pipeline timing parameters.

## Decision
1. **Non-blocking `room.sid`**: LiveKit's `ctx.room.sid` is awaited inside a detached background task (`asyncio.create_task`) so the agent entrypoint and greeting can start immediately without a 30-second delay.
2. **Audio Track Isolation**: On `track_published` and `track_subscribed`, if the participant's identity starts with `agent_` or `human_`, the agent explicitly calls `publication.set_subscribed(False)`. This ensures the AI never listens to or speaks over other support agents.
3. **DOM Audio GC Prevention**: In the customer client, `track.attach()` elements must be explicitly appended to `document.body` to prevent browser garbage collection of the audio context.
4. **Escalation Regex**: Escalation intent uses a strict word-boundary regex (`\b(speak to a human|talk to a human|transfer me|...)\b`) to prevent false-positives like "superhuman".
5. **Pipeline Timings**:
   - `interrupt_speech_duration = 0.7s`
   - `interrupt_min_words = 2`
   - `min_endpointing_delay = 0.6s`
   - `preemptive_synthesis = False`

## Consequences
- Preserves responsive 1-second conversational turn latency.
- Prevents audio echo feedback loops in multi-party conference rooms.
