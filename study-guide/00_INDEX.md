# 📚 Study Guide — LiveKit Voice AI Support Agent
## Your Complete Beginner's Roadmap to Understanding This Project

> **Who this is for:** You built this project (or had it built for you), and now you want to understand it *properly* — what every line does, why, and how it fits together.
>
> **How to read this:** Go in order. Each file builds on the last. Don't skip ahead. When you see a code block, read the comments — they are the lesson.

---

## 📋 Table of Contents

| File | What It Covers | Time |
|------|---------------|------|
| **00_INDEX.md** ← *You are here* | Architecture diagram, how to run, overall flow | 10 min |
| 01_PROJECT_MAP.md | Every file listed, its job, who imports it | 10 min |
| 02_PYTHON_FOUNDATIONS.md | Core Python (async, decorators, env vars, classes…) | 45 min |
| 03_LIVEKIT_DEEPDIVE.md | LiveKit rooms, agents, tracks, VAD, events | 30 min |
| 04_LANGCHAIN_DEEPDIVE.md | LangChain: prompts, ChatOpenAI, LLM chaining | 25 min |
| 05_LANGGRAPH_DEEPDIVE.md | LangGraph: state machines, nodes, edges, your graph | 35 min |
| 06_RAG_AND_EMBEDDINGS_DEEPDIVE.md | Embeddings, vector search, ChromaDB, RAG for FAQs | 30 min |
| 07_FASTAPI_DEEPDIVE.md | FastAPI: routes, Pydantic, tokens, your endpoints | 25 min |
| 08_SUPABASE_DEEPDIVE.md | Supabase PostgreSQL: call sessions, transcripts, latency | 20 min |
| 10_HANDOFF_AND_ESCALATION.md | Full escalation flow: trigger → silence AI → handoff → resume | 25 min |
| 11_WALKTHROUGH_config.md | agent/config.py — env var loading + validation | 15 min |
| 12_WALKTHROUGH_state.md | agent/state.py — the conversation memory schema | 15 min |
| 13_WALKTHROUGH_nodes.md | agent/nodes.py — every conversation handler, deeply commented | 40 min |
| 14_WALKTHROUGH_graph_builder.md | agent/graph_builder.py — assembling the state machine | 30 min |
| 15_WALKTHROUGH_main.md | agent/main.py — the entry point, step by step | 40 min |
| 16_WALKTHROUGH_chroma.md | agent/chroma_client.py + embed_documents.py | 20 min |
| 17_WALKTHROUGH_handoff.md | agent/handoff.py — session mute flag + Supabase sync | 20 min |
| 18_WALKTHROUGH_backend.md | backend/main.py, routes.py, database.py | 35 min |
| 19_WALKTHROUGH_frontend.md | frontend/livekit_client.js, App.jsx | 30 min |
| GLOSSARY.md | Every library/concept in 2-3 sentences | Anytime |

**Total: ~7 hours of focused learning.** Do it in chunks — one or two files per session.

---

## 🏗️ Architecture Diagram

This is the **big picture** of how data flows when a customer calls:

```
 CUSTOMER'S BROWSER (React Frontend)
 ┌──────────────────────────────────────────────────────────────┐
 │  App.jsx                                                     │
 │   └─ handleJoin() ───► POST /api/token ──► FastAPI Backend   │
 │   └─ LiveKitHelper.connect() ─────────► LiveKit Cloud (wss://│
 │       (WebSocket: audio streams both ways)                   │
 └──────────────────────────────────────────────────────────────┘
                           │  wss:// audio stream
                           ▼
 LIVEKIT CLOUD SERVER (audio routing hub)
 ┌──────────────────────────────────────────────────────────────┐
 │  Routes audio between customer and AI agent                  │
 │  Manages rooms, tracks, participants                         │
 └──────────────────────────────────────────────────────────────┘
                           │
                           ▼
 AI AGENT PROCESS  (agent/main.py — runs as a background worker)
 ┌──────────────────────────────────────────────────────────────┐
 │  VoicePipelineAgent:                                         │
 │                                                              │
 │  1. VAD (Silero) ── "Is the customer speaking right now?"    │
 │  2. STT (Deepgram) ── Voice → "I want to book an appt"      │
 │  3. LLM (LangGraphLLM wrapper)                               │
 │      │                                                       │
 │      │   LangGraph State Machine (graph_builder.py)          │
 │      │   START → entry_router                                │
 │      │              │                                        │
 │      │              ├──► greeting → END                      │
 │      │              └──► route_input (router_node)           │
 │      │                       │                               │
 │      │                       ├──► faq_node ── ChromaDB       │
 │      │                       ├──► verify_customer ── FastAPI │
 │      │                       ├──► registration ── FastAPI    │
 │      │                       ├──► appointment               │
 │      │                       ├──► complaint ── FastAPI       │
 │      │                       ├──► escalate ── handoff.py     │
 │      │                       └──► general_chat ── Groq LLM   │
 │      │                                                       │
 │  4. TTS (Deepgram) ── Response text → Audio stream           │
 │                                                              │
 │  SIDE EFFECTS (background, never block audio):               │
 │    • transcript line ──► Supabase (call_transcripts)         │
 │    • latency timing ───► Supabase (latency_logs)             │
 │    • escalation flag ──► handoff.py dict + Supabase          │
 └──────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
 FASTAPI BACKEND                   SUPABASE (Cloud PostgreSQL)
 backend/main.py + routes.py       ┌─────────────────────────┐
 ┌─────────────────────────┐       │  call_sessions          │
 │ POST /api/token         │       │  call_transcripts       │
 │ GET  /api/rooms         │       │  latency_logs           │
 │ POST /api/tickets       │       └─────────────────────────┘
 │ GET  /api/customers     │
 │ GET  /health            │       SQLITE (local file)
 └─────────────────────────┘       ┌─────────────────────────┐
                                   │  customers table        │
 CHROMADB (agent/chroma_db/)       │  tickets table          │
 ┌─────────────────────────┐       └─────────────────────────┘
 │ hours.txt  → embedding  │
 │ location.txt → embedding│
 │ pricing.txt  → embedding│
 │ refunds.txt  → embedding│
 └─────────────────────────┘
```

---

## 🚀 "How To Run This Project" — Step By Step

When you type `python main.py dev` in the `agent/` folder, this is the **exact** sequence of events:

### Step 1: Python Starts, Top-to-Bottom Imports Run

```
python agent/main.py dev
      │
      ▼
Python reads main.py top to bottom...
```

In order, this is what gets imported/initialized:

1. **Standard library**: `asyncio`, `logging`, `os`, `sys`, `uuid`, `datetime`
2. **Event loop safety check** (lines 36-39): Ensures asyncio works on Python 3.12+ even inside worker processes
3. **Path manipulation** (lines 47-49): Adds `backend/` to Python's search path so `from database import ...` works from `agent/`
4. **`.env` loading** (line 53): Reads `LIVEKIT_URL`, `GROQ_API_KEY` etc. from root `.env` file into `os.environ`
5. **Logging setup** (lines 60-62): All future log messages now go to terminal AND `logs/app.log`
6. **LiveKit imports**: The `livekit` Python SDK (rooms, rtc, plugins)
7. **`config.py`** is imported: reads all env vars into a `Settings` object
8. **`graph_builder.py`** is imported: builds AND compiles the entire LangGraph state machine right here at startup
9. **`database.py`** (from backend folder): Supabase client + SQLite helpers are loaded
10. **Silero VAD** model is loaded into RAM (takes 1-2 seconds)
11. **ChromaDB warm-up**: A dummy FAQ query runs to load the SentenceTransformer model (avoids 6-9s delay on first real call)
12. **`settings.validate_config()`**: Checks all required API keys exist — exits with clear error message if anything is missing

### Step 2: LiveKit CLI Takes Over

```python
cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, ...))
```

This starts a **LiveKit Worker** — a long-running background process that:
- Connects to the LiveKit Cloud server using your `LIVEKIT_URL` + credentials
- Sits and waits for "job dispatch" events meaning: "a customer joined a room, please handle this call"

### Step 3: A Customer Joins

The customer opens the React frontend (`npm start` in `frontend/`), types their name, and clicks "Start Call":
1. Frontend calls `POST /api/token` on the FastAPI backend (`uvicorn main:app` in `backend/`)
2. Backend generates a signed JWT token (like a secure visitor pass for the LiveKit room)
3. Frontend connects to LiveKit Cloud over WebSocket using that token

LiveKit sees a customer in a room and **dispatches the job** to our waiting agent worker.

### Step 4: `entrypoint(ctx)` Is Called

This is our main call handler function in `agent/main.py`:

```
entrypoint(ctx: JobContext)
    │
    ├─ Generate session_id (UUID — unique call ID)
    ├─ Record call_start_time
    ├─ Create Supabase call_sessions row  ──────────────► Supabase
    ├─ await ctx.connect() → join the LiveKit room
    ├─ [background] fetch room SID and save to Supabase
    ├─ Build VoicePipelineAgent (VAD + STT + LangGraphLLM + TTS)
    ├─ Register all event listeners (@agent.on, @ctx.room.on)
    ├─ agent.start(ctx.room) → begin listening for audio
    ├─ await agent.say("Hello! Welcome to Epoxcel...") → greet
    └─ Enter main loop (check for timeout every 30 seconds)
```

### Step 5: The Voice Pipeline Loop (for each customer utterance)

```
Customer speaks
     │
     ▼
VAD (Silero) detects speech → fires "user_started_speaking" event
     │                         (latency timer starts)
     ▼
Customer stops speaking → fires "user_stopped_speaking" event
     │                    (STT timer ends, LLM timer starts)
     ▼
Deepgram STT → converts audio to text
     │
     ▼
LangGraphLLM._run() is called:
     ├─ Check: is handoff active? → if yes, stay silent
     ├─ Convert messages to LangChain format
     ├─ Run graph: ainvoke({messages: [...]}) 
     │   → entry_router → route_input → [correct node] → END
     ├─ Get AIMessage from result
     └─ Stream response word-by-word into LiveKit event channel
     │
     ▼
"agent_started_speaking" fires (LLM timer ends, TTS timer starts)
     │
     ▼
Deepgram TTS → converts text to audio → streams to customer
     │
     ▼
"agent_stopped_speaking" fires (TTS timer ends, latency summary logged)
     │
     ▼  (in background, simultaneously)
"user_speech_committed" already fired → saves transcript to Supabase
"agent_speech_committed" fires → saves agent response to Supabase
LatencyTracker._save_to_db() → saves timing to Supabase
```

### Step 6: Call Ends (Normal or Timeout)

```
Room disconnects OR timeout detected
     │
     ▼
end_call_gracefully(session_id, start_time, status, reason)
     │
     ├─ Calculate duration_seconds
     ├─ generate_call_summary(session_id):
     │   ├─ get_full_transcript() ──► Supabase (read)
     │   ├─ Format as "User: ...\nAgent: ..."
     │   └─ groq_llm.invoke(summarize prompt) ──► Groq API
     │
     └─ complete_call_session() ──► Supabase (update)
             status, duration, summary, disconnect_reason
```

---

## 🎯 The Three Big Ideas (bookmark these)

Before diving into the details, make sure you understand these three concepts at a high level:

1. **Async/await**: Everything that talks to a network (LiveKit, Groq, Supabase, Deepgram) could take variable time. `async/await` means "start this, and while waiting, go do other things". Without it, the voice call would freeze every time the LLM thinks.

2. **The LangGraph State Machine**: Instead of a simple "if user says X do Y" chatbot, this project uses a graph of states. The conversation is always "in a flow" — greeting → verify → booking, for example. Each state is a "node", and routing between nodes is done by "edges" with logic.

3. **Fire-and-forget side effects**: The transcript saves, latency logs, and Supabase updates all run in the background using `asyncio.ensure_future()`. They never block the audio pipeline. If Supabase is down, the call still works — we just lose the logs. This is called "graceful degradation".

---

*Next up → [01_PROJECT_MAP.md](./01_PROJECT_MAP.md)*
