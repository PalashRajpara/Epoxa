# 03 — LiveKit Deep Dive: The Voice Infrastructure Layer

> See [02_PYTHON_FOUNDATIONS.md](./02_PYTHON_FOUNDATIONS.md) for async/await fundamentals
> before reading this file — you'll need them to understand event-driven voice pipelines.

---

## What Is LiveKit?

LiveKit is a **real-time communication platform** — think of it as the "audio switchboard"
that connects your customer's browser microphone to the AI agent, and the AI agent's
synthesized speech back to the customer's speakers.

Without LiveKit, you would need to:
1. Set up WebSocket servers yourself
2. Handle audio codec negotiation (WebRTC is notoriously complex)
3. Build audio routing, buffering, and track management from scratch
4. Handle reconnections, NAT traversal, TURN/STUN servers...

LiveKit handles all of that. You just:
1. Create a "room"
2. Connect participants to the room
3. Publish/subscribe to audio "tracks"

The LiveKit Python SDK adds a special layer on top — the **Agents framework** — which
provides ready-made abstractions for building voice AI pipelines.

---

## Core Concepts

### Room

A **Room** is a virtual "call space" where participants meet. In this project:
- One room = one customer support call
- The customer joins via their browser (using the JavaScript SDK)
- The AI agent joins via the Python worker process

Rooms are identified by a **name** (e.g., `support-user-abc123`) and a **SID** (LiveKit's
internal session ID, e.g., `RM_xxxxxxxxxxx`).

### Track

A **Track** is a stream of audio (or video) data. In a voice call:
- The customer's microphone → **local audio track** published to the room
- The AI agent's text-to-speech output → **remote audio track** the customer subscribes to

Tracks are the actual bytes of audio flowing in real-time over WebRTC.

### Worker and Job

A **Worker** is a long-running Python process that:
1. Connects to the LiveKit server
2. Registers itself as capable of handling certain types of jobs
3. Waits for **job dispatch** events

When a participant (customer) joins a room, LiveKit dispatches a **Job** to one of the waiting workers. The worker runs the `entrypoint` function to handle that call.

### VoicePipelineAgent

This is the central object in the agent code. It wires together:

```
Customer Audio → VAD → STT → LLM → TTS → Customer Speakers
```

You create it with plugins for each stage:

```python
agent = VoicePipelineAgent(
    vad=vad_plugin,     # Voice Activity Detection (Silero)
    stt=stt_plugin,     # Speech to Text (Deepgram)
    llm=llm_plugin,     # Language Model (our LangGraphLLM wrapper)
    tts=tts_plugin,     # Text to Speech (Deepgram)
    chat_ctx=initial_ctx,
    preemptive_synthesis=True,   # Start TTS while LLM is still generating
    min_endpointing_delay=0.5    # Wait at least 0.5s after silence before processing
)
```

### ChatContext

A **ChatContext** is LiveKit's representation of the conversation history —
a list of messages with roles (`system`, `user`, `assistant`). It's analogous to
the `messages` array you send to OpenAI's API.

### Event System

LiveKit fires events at key moments. You listen for them with the `@object.on("event")` decorator pattern. The agent object fires events about the pipeline; the room object fires events about participants and connectivity.

---

## The LiveKit Pipeline in This Project — Commented Code

### Setting up the pipeline — `agent/main.py`

```python
# agent/main.py — inside entrypoint()

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────
# llm.ChatContext() creates a new conversation history object.
# We immediately add the system prompt — this tells the AI how to behave.
# 'system' role = instructions for the AI, not shown to the user.
# All subsequent conversation messages will be added on top of this.
initial_ctx = llm.ChatContext().append(
    role="system",
    text=(
        "You are Epixa, a helpful customer support agent for Epoxcel. "
        "Keep your responses concise, friendly, and conversational since "
        "this is a voice-based interaction. Avoid listing bullet points; "
        "speak in natural, complete sentences."
    )
)

# ─── SPEECH-TO-TEXT ───────────────────────────────────────────────────────────
# deepgram.STT creates the Deepgram speech recognition plugin.
# Deepgram listens to the customer's audio stream and converts it to text.
# The api_key is read from our .env file via the settings object.
stt_plugin = deepgram.STT(
    api_key=settings.DEEPGRAM_STT_API_KEY
)

# ─── LLM (OUR CUSTOM WRAPPER) ─────────────────────────────────────────────────
# LangGraphLLM is our custom class defined in graph_builder.py.
# It wraps the LangGraph state machine so LiveKit thinks it's a normal LLM.
# thread_id = session_id (the UUID for this call) — this is how LangGraph
# knows which conversation's memory to use for each call.
llm_plugin = LangGraphLLM(
    graph=compiled_graph,
    thread_id=session_id     # Each call gets its own conversation thread
)

# ─── TEXT-TO-SPEECH ───────────────────────────────────────────────────────────
# deepgram.TTS converts the agent's text responses back into audio.
# model="aura-asteria-en" = Deepgram's natural-sounding female English voice.
# use_streaming=True = start sending audio to the customer as soon as the
# first chunk of text is ready, rather than waiting for the full response.
# This dramatically reduces the perceived latency ("time to first sound").
tts_plugin = deepgram.TTS(
    api_key=settings.DEEPGRAM_TTS_API_KEY,
    model="aura-asteria-en",
    use_streaming=True
)

# ─── VOICE ACTIVITY DETECTION ─────────────────────────────────────────────────
# VAD_PLUGIN is the Silero model pre-loaded at startup (see line ~98 of main.py).
# VAD constantly analyzes the incoming audio stream and answers:
# "Is the customer speaking right now, or is this silence/background noise?"
# This is what triggers user_started_speaking and user_stopped_speaking events.
vad_plugin = VAD_PLUGIN

# ─── ASSEMBLE THE PIPELINE ────────────────────────────────────────────────────
# VoicePipelineAgent wires everything together. The data flow is:
# customer mic audio → VAD detects speech → STT transcribes → LLM generates →
# TTS synthesizes → audio streamed back to customer
agent = VoicePipelineAgent(
    vad=vad_plugin,
    stt=stt_plugin,
    llm=llm_plugin,
    tts=tts_plugin,
    chat_ctx=initial_ctx,
    preemptive_synthesis=True,  # Start TTS while LLM is still generating tokens
    min_endpointing_delay=0.5   # Require at least 0.5s silence before processing
)
```

**Clean version (production):**
```python
initial_ctx = llm.ChatContext().append(
    role="system",
    text="You are Epixa, a helpful customer support agent for Epoxcel..."
)
stt_plugin = deepgram.STT(api_key=settings.DEEPGRAM_STT_API_KEY)
llm_plugin = LangGraphLLM(graph=compiled_graph, thread_id=session_id)
tts_plugin = deepgram.TTS(api_key=settings.DEEPGRAM_TTS_API_KEY, model="aura-asteria-en", use_streaming=True)
agent = VoicePipelineAgent(vad=VAD_PLUGIN, stt=stt_plugin, llm=llm_plugin, tts=tts_plugin, chat_ctx=initial_ctx, preemptive_synthesis=True, min_endpointing_delay=0.5)
```

---

### Agent Event Listeners — `agent/main.py`

```python
# agent/main.py — transcript capture events

# ─── USER SPEECH COMMITTED ────────────────────────────────────────────────────
# "committed" means the VAD confirmed the user finished speaking a full utterance.
# This fires ONCE per utterance, after the STT has the full text.
# (contrast with "user_stopped_speaking" which fires when silence starts)
@agent.on("user_speech_committed")
def on_user_speech_committed(msg: llm.ChatMessage):
    # msg.content contains the transcribed text from Deepgram
    # We check isinstance because content could be a list (for multimodal) or str
    text = msg.content if isinstance(msg.content, str) else ""
    if not text.strip():
        return  # Nothing to save if it's just noise/empty

    # message_sequence is a list with one integer: [0]
    # We use a list instead of a plain integer because Python closures can't
    # reassign outer-scope variables directly in nested functions.
    # A list is mutable, so message_sequence[0] += 1 works inside this closure.
    message_sequence[0] += 1

    # Update the activity timestamp — resets the session timeout countdown
    last_activity_time[0] = datetime.now(timezone.utc)

    logger.info(f"[Transcript] USER (#{message_sequence[0]}): {text[:80]}")

    # Save to Supabase in the background — never blocks the audio pipeline
    asyncio.ensure_future(
        _save_transcript_async(session_id, "user", text, message_sequence[0])
    )


# ─── AGENT SPEECH COMMITTED ───────────────────────────────────────────────────
# Fires when the agent finishes speaking a complete utterance.
# We save the agent's response to the transcript, same as user messages.
@agent.on("agent_speech_committed")
def on_agent_speech_committed(msg: llm.ChatMessage):
    text = msg.content if isinstance(msg.content, str) else ""
    if not text.strip():
        return

    message_sequence[0] += 1
    logger.info(f"[Transcript] AGENT (#{message_sequence[0]}): {text[:80]}")

    asyncio.ensure_future(
        _save_transcript_async(session_id, "agent", text, message_sequence[0])
    )
```

```python
# agent/main.py — latency tracking events

# ─── PIPELINE TIMING EVENTS ───────────────────────────────────────────────────
# These four events fire in order during each voice pipeline turn:
#   user_started_speaking → user_stopped_speaking → agent_started_speaking → agent_stopped_speaking

@agent.on("user_started_speaking")
def on_user_started_speaking():
    # User began speaking — Deepgram STT is now receiving audio
    logger.info("🎙️ [Event] User started speaking...")
    latency_tracker.reset()      # Clear timings from the previous turn
    latency_tracker.start("stt") # Start the STT timing clock

@agent.on("user_stopped_speaking")
def on_user_stopped_speaking():
    # User stopped — Deepgram is processing the audio segment into text
    # STT ends here; LLM begins immediately (we don't wait for the full transcript)
    logger.info("🎙️ [Event] User stopped speaking (processing...)")
    latency_tracker.end("stt")   # Record how long STT took
    latency_tracker.start("llm") # Start the LLM timing clock

@agent.on("agent_started_speaking")
def on_agent_started_speaking():
    # Agent is now outputting audio — this means:
    # 1. The LLM generated a response (LLM is done)
    # 2. TTS started converting text to audio (TTS begins)
    logger.info("🤖 [Event] Agent started speaking...")
    latency_tracker.end("llm")   # Record how long the LLM took
    latency_tracker.start("tts") # Start the TTS timing clock

@agent.on("agent_stopped_speaking")
def on_agent_stopped_speaking():
    # Agent finished speaking — the customer can talk again
    logger.info("🤖 [Event] Agent stopped speaking.")
    latency_tracker.end("tts")         # Record TTS duration
    latency_tracker.print_summary()    # Log: stt=312ms | llm=489ms | tts=203ms | total=1004ms
```

---

### Room Event Listeners — `agent/main.py`

```python
# agent/main.py — room-level events (participants, connectivity)

# ─── PARTICIPANT CONNECTED ────────────────────────────────────────────────────
# Fires when ANY participant joins the room.
# In our setup, this will be the customer — the agent is already in the room.
@ctx.room.on("participant_connected")
def on_participant_connected(participant: rtc.RemoteParticipant):
    logger.info(f"[Room Event] Participant JOINED: {participant.identity}")
    # Reset the activity timer — someone just arrived!
    last_activity_time[0] = datetime.now(timezone.utc)
    # Update Supabase with the participant's name (we didn't know it at call start)
    asyncio.ensure_future(
        _update_session_participant_async(session_id, participant.name or participant.identity)
    )

# ─── PARTICIPANT DISCONNECTED ─────────────────────────────────────────────────
# Fires when a participant leaves the room.
# This doesn't immediately end the call — the room stays open briefly
# in case they reconnect. The main loop handles actual call termination.
@ctx.room.on("participant_disconnected")
def on_participant_disconnected(participant: rtc.RemoteParticipant):
    logger.info(f"[Room Event] Participant DISCONNECTED: {participant.identity}")
    logger.info("[Room Event] Waiting to see if they reconnect...")

# ─── RECONNECTION EVENTS ──────────────────────────────────────────────────────
# These refer to the AGENT's own connection to the LiveKit server,
# not the customer's. LiveKit handles reconnection automatically.
@ctx.room.on("reconnecting")
def on_room_reconnecting():
    reconnect_attempts[0] += 1
    logger.warning(
        f"[Room Event] Agent connection unstable — reconnecting "
        f"(attempt {reconnect_attempts[0]}/{MAX_RECONNECT_ATTEMPTS})"
    )

@ctx.room.on("reconnected")
def on_room_reconnected():
    reconnect_attempts[0] = 0    # Reset counter on success
    logger.info("[Room Event] Agent reconnected successfully ✓")

# ─── ROOM DISCONNECTED ────────────────────────────────────────────────────────
# The room itself fully disconnected — this is the final end-of-call event.
# The main while loop will detect this and call end_call_gracefully().
@ctx.room.on("disconnected")
def on_room_disconnected(reason: rtc.DisconnectReason = None):
    reason_str = str(reason) if reason else "unknown"
    logger.info(f"[Room Event] Room DISCONNECTED. Reason: {reason_str}")
```

---

### Handoff Track Events — `agent/main.py`

```python
# agent/main.py — track events for human agent handoff

# ─── TRACK PUBLISHED ──────────────────────────────────────────────────────────
# When ANY participant publishes a track (starts streaming audio),
# this event fires. We use it to prevent the AI from accidentally subscribing
# to and "hearing" the human support agent's audio.
@ctx.room.on("track_published")
def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
    # Human agents join the room with identities starting with "agent_" or "human_"
    # (set in routes.py when generating their JWT token)
    if participant.identity.startswith("agent_") or participant.identity.startswith("human_"):
        logger.info(f"[Handoff] Ignoring published audio from human agent: {participant.identity}")
        # set_subscribed(False) means: "don't give me this audio track"
        # Without this, the AI would hear the human agent talking and respond to them!
        publication.set_subscribed(False)

# ─── DATA RECEIVED ────────────────────────────────────────────────────────────
# Participants can send non-audio "data messages" over the LiveKit room.
# The human agent dashboard uses this to send control signals to the AI.
@ctx.room.on("data_received")
def on_data_received(data_packet: rtc.DataPacket):
    try:
        # data_packet.data is raw bytes — decode to string, then parse as JSON
        payload_str = data_packet.data.decode("utf-8")
        payload = json.loads(payload_str)
        action = payload.get("action")

        if action == "resume":
            # Human agent clicked "Resume AI" in the dashboard
            # Turn off handoff mode so the AI starts responding again
            handoff.set_handoff_active(session_id, False)

            async def _speak_resume():
                await asyncio.sleep(0.3)   # Brief pause for flag to propagate
                resume_text = "Welcome back! I'm back on the line. How can I help?"
                agent.chat_ctx.append(role="assistant", text=resume_text)
                await agent.say(resume_text, allow_interruptions=True)

            asyncio.ensure_future(_speak_resume())

        elif action == "handoff":
            # Human agent clicked "Take Over" in the dashboard
            # Set handoff mode = AI goes silent
            handoff.set_handoff_active(session_id, True)

    except Exception as e:
        logger.error(f"[Handoff] Error parsing data packet: {e}")
```

---

### Starting the Agent and the Main Loop — `agent/main.py`

```python
# agent/main.py — the end of entrypoint()

# ─── START THE AGENT ──────────────────────────────────────────────────────────
# This begins the pipeline — VAD starts listening, events are armed.
# The agent doesn't say anything yet; it's just listening.
agent.start(ctx.room)

# Wait 300ms for audio channels to stabilize before speaking.
# Without this, the greeting audio can get cut off at the beginning.
await asyncio.sleep(0.3)

# Save the greeting message to LangGraph's memory so the graph knows
# the call has been greeted. This prevents the greeting_node from
# firing again if the conversation loops back to START.
greeting_text = "Hello! Welcome to Epoxcel. My name is Epixa. How can I help you today?"
await compiled_graph.aupdate_state(
    {"configurable": {"thread_id": session_id}},
    {"messages": [AIMessage(content=greeting_text)], "current_flow": "greeting"}
)

# Add the greeting to LiveKit's ChatContext too (keeps both in sync)
initial_ctx.append(role="assistant", text=greeting_text)

# Actually speak the greeting — this starts TTS and streams audio to the customer
await agent.say(greeting_text, allow_interruptions=True)

# ─── MAIN CALL LOOP ───────────────────────────────────────────────────────────
# We stay in this loop until the call ends.
# Every 30 seconds, check if the customer has been silent too long.
call_ended = False
timeout_seconds = SESSION_TIMEOUT_MINUTES * 60
check_interval = 30

try:
    # Loop condition: keep going while the room is connected
    while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
        # Sleep 30 seconds before checking for timeout
        # During this sleep, the event loop runs other tasks (audio pipeline, etc.)
        await asyncio.sleep(check_interval)

        # Calculate how long since the customer last spoke
        silence_duration = (datetime.now(timezone.utc) - last_activity_time[0]).total_seconds()

        if silence_duration > timeout_seconds:
            # Customer has been silent for too long — end the call politely
            await agent.say(
                "It seems you may have stepped away. I'll end our session now. "
                "Feel free to call back anytime. Goodbye!",
                allow_interruptions=False
            )
            await asyncio.sleep(3)  # Give TTS time to finish before disconnecting

            await end_call_gracefully(
                session_id=session_id,
                call_start_time=call_start_time,
                status="timeout",
                disconnect_reason=f"Timed out after {SESSION_TIMEOUT_MINUTES} minutes"
            )
            call_ended = True
            break  # Exit the while loop

    # If we exited the loop because the room disconnected (not timeout):
    if not call_ended:
        await end_call_gracefully(
            session_id=session_id,
            call_start_time=call_start_time,
            status="completed",
            disconnect_reason="participant_disconnected"
        )

except Exception as e:
    logger.error(f"[Agent] Unexpected error in call loop: {e}", exc_info=True)
    if not call_ended:
        await end_call_gracefully(..., status="error", disconnect_reason=str(e))
```

---

### The Custom LLM Wrapper — `agent/graph_builder.py`

This is the bridge between LiveKit and LangGraph. LiveKit expects its LLM to implement
a specific interface; we subclass it to run our LangGraph state machine instead:

```python
# agent/graph_builder.py

# ─── LangGraphLLM ─────────────────────────────────────────────────────────────
# Subclassing llm.LLM means LiveKit treats this as a normal LLM plugin.
# Any plugin that implements the .chat() method can be used in VoicePipelineAgent.
class LangGraphLLM(llm.LLM):
    def __init__(self, graph, thread_id: str):
        super().__init__()           # Must call parent __init__ for LiveKit internals
        self.graph = graph           # The compiled LangGraph state machine
        self.thread_id = thread_id   # The session ID (= conversation memory key)

    # LiveKit calls .chat() whenever it needs a response.
    # It passes the current ChatContext (conversation history).
    # We return a LangGraphStream object (which does the actual work).
    def chat(self, *, chat_ctx: llm.ChatContext, tools=None, **kwargs) -> llm.LLMStream:
        return LangGraphStream(self, chat_ctx, self.graph)


# ─── LangGraphStream ──────────────────────────────────────────────────────────
# Subclassing llm.LLMStream means we implement the streaming interface.
# LiveKit expects tokens to come one at a time (like OpenAI streaming).
# We simulate this by splitting the LangGraph response into words.
class LangGraphStream(llm.LLMStream):
    def __init__(self, llm_obj, chat_ctx, graph):
        from livekit.agents.llm.llm import DEFAULT_API_CONNECT_OPTIONS
        super().__init__(
            llm=llm_obj,
            chat_ctx=chat_ctx,
            fnc_ctx=None,                        # No function-calling context needed
            conn_options=DEFAULT_API_CONNECT_OPTIONS
        )
        self.graph = graph

    # _run() is called by LiveKit when it's ready for tokens.
    # We fill self._event_ch (an event channel) with ChatChunk objects.
    # LiveKit reads from this channel and feeds each chunk into TTS.
    async def _run(self) -> None:
        try:
            # Bail out silently if handoff is active (human is talking)
            if is_handoff_active(self._llm.thread_id):
                logger.info(f"[GraphStream] Handoff active. Muting AI response.")
                return

            # Convert LiveKit ChatContext messages to LangChain message objects.
            # LangGraph expects LangChain format; LiveKit uses its own format.
            lc_messages = []
            for msg in self._chat_ctx.messages:
                if msg.role == "system":
                    lc_messages.append(SystemMessage(content=msg.content))
                elif msg.role == "user":
                    lc_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    lc_messages.append(AIMessage(content=msg.content))

            # Run the graph — ainvoke is the async version of invoke.
            # config["configurable"]["thread_id"] is how LangGraph knows which
            # conversation memory (checkpointer state) to use.
            config = {"configurable": {"thread_id": self._llm.thread_id}}
            result = await self.graph.ainvoke({"messages": lc_messages}, config=config)

            # The graph returns a dict with updated state. We read the last AIMessage.
            messages = result.get("messages", [])
            if messages and isinstance(messages[-1], AIMessage):
                content = messages[-1].content
                words = content.split(" ")
                for i, word in enumerate(words):
                    # Build a word chunk in LiveKit's expected format
                    space = " " if i > 0 else ""
                    chunk_text = space + word

                    choice_delta = llm.ChoiceDelta(role="assistant", content=chunk_text)
                    choice = llm.Choice(delta=choice_delta, index=0)
                    chunk = llm.ChatChunk(request_id="langgraph", choices=[choice])

                    # Push the word chunk into the event channel.
                    # LiveKit reads from this channel and starts TTS as soon as the
                    # first words arrive — this is what enables streaming TTS.
                    self._event_ch.send_nowait(chunk)

                    # Yield 5ms to the event loop so it can handle other work.
                    # Without this, the for loop would consume the entire event loop
                    # and block audio from flowing.
                    await asyncio.sleep(0.005)

        except Exception as e:
            logger.error(f"Error in LangGraph stream executor: {str(e)}")
        finally:
            # MUST close the channel or LiveKit hangs waiting for more tokens forever.
            self._event_ch.close()
```

---

## Common Gotchas for LiveKit Beginners

| Gotcha | What happens | Fix |
|--------|-------------|-----|
| Forgetting `await ctx.connect()` | Agent tries to access room before connection is ready | Always `await` this first |
| Not closing `_event_ch` in `finally` | TTS pipeline hangs waiting for tokens that never come | Use `finally: self._event_ch.close()` |
| Running a blocking sync call without `run_in_executor` | Event loop freezes; audio stutters | Wrap sync DB calls in `await loop.run_in_executor(None, lambda: ...)` |
| Using `ctx.room.sid` before `await ctx.connect()` | Returns a coroutine object, not the actual SID string | Only access room.sid after connecting, and in a background task |
| Subscribing to the human agent's audio track | AI hears the human and generates confused responses | Use `track_published` event to call `set_subscribed(False)` |
| Not pre-warming the embedding model | First call has a 6-9 second delay before FAQ answers work | Run a dummy `query_faq("warmup", n_results=1)` at startup |

---

*Next up → [04_LANGCHAIN_DEEPDIVE.md](./04_LANGCHAIN_DEEPDIVE.md)*
