# 01 — Project Map: Every File and Its Purpose

> Think of this file as the treasure map. Before you study any individual file,
> you need to know where it lives, what it does, and how it connects to its neighbors.

---

## 📁 Full Directory Tree

```
livekit-voice-ai-support/         ← Project root
├── .env                          ← YOUR real API keys (never commit this)
├── .env.example                  ← Template showing what keys are needed
├── .gitignore                    ← Tells git what NOT to save
├── README.md                     ← Project overview
│
├── agent/                        ← The AI voice agent (Python)
│   ├── main.py                   ← ENTRY POINT: starts the LiveKit worker
│   ├── config.py                 ← Loads .env, validates all API keys
│   ├── state.py                  ← Defines what "memory" the agent keeps
│   ├── graph_builder.py          ← Assembles the LangGraph state machine
│   ├── nodes.py                  ← Individual conversation handlers (FAQ, booking, etc.)
│   ├── handoff.py                ← Human escalation: mutes AI, syncs with Supabase
│   ├── chroma_client.py          ← Connects to ChromaDB vector database
│   ├── embed_documents.py        ← ONE-TIME SCRIPT: loads FAQ .txt files into ChromaDB
│   ├── utils.py                  ← Logging setup + LatencyTracker class
│   ├── requirements.txt          ← Python package dependencies for agent
│   │
│   ├── faq_docs/                 ← Raw text files that become the FAQ knowledge base
│   │   ├── hours.txt             ← "We are open Mon-Fri 9am-6pm IST..."
│   │   ├── location.txt          ← Address and directions
│   │   ├── pricing.txt           ← Product/service pricing info
│   │   └── refunds.txt           ← Refund policy
│   │
│   └── chroma_db/                ← Where ChromaDB stores its vector embeddings (auto-created)
│       └── (binary files — don't edit these manually)
│
├── backend/                      ← FastAPI REST API (Python)
│   ├── main.py                   ← ENTRY POINT: starts the FastAPI/uvicorn server
│   ├── routes.py                 ← All API endpoints (token, rooms, customers, tickets)
│   ├── database.py               ← SQLite + Supabase database operations
│   ├── utils.py                  ← Logging + LatencyTracker (shared with agent)
│   ├── schema.sql                ← Supabase PostgreSQL table definitions
│   ├── requirements.txt          ← Python package dependencies for backend
│   └── voice_support.db          ← SQLite file (auto-created on first run)
│
├── frontend/                     ← React customer-facing web app (JavaScript)
│   ├── src/
│   │   ├── App.jsx               ← Root component: handles call join/leave lifecycle
│   │   ├── livekit_client.js     ← LiveKit SDK wrapper: connects, manages audio tracks
│   │   ├── index.js              ← React entry point (renders App into the DOM)
│   │   └── components/           ← Sub-components (JoinRoom screen, CallScreen, etc.)
│   └── package.json              ← JavaScript/npm package dependencies
│
├── dashboard/                    ← Human agent support dashboard (React)
│   └── src/                      ← Similar to frontend but for support staff
│
└── logs/                         ← Log files written at runtime
    ├── app.log                   ← General application logs
    └── latency.log               ← STT/LLM/TTS timing measurements
```

---

## 📄 File-by-File Responsibility Guide

### `agent/main.py` — The Main Brain

**What it does:** This is where everything starts. When you run `python main.py dev`, this file:
- Loads all the pieces (config, graph, database, plugins)
- Starts the LiveKit worker process
- Handles every incoming call via the `entrypoint(ctx)` function
- Manages the full call lifecycle: greeting → conversation → summary → cleanup

**Imports from:** `config`, `graph_builder`, `database` (backend), `utils`, `handoff`, `livekit.*`, `langchain_openai`

**Imported by:** Nothing — this is the top of the chain.

---

### `agent/config.py` — Settings Manager

**What it does:** Reads all API keys from the `.env` file and exposes them as a `Settings` object. Also runs a startup check to make sure nothing is missing.

**Key line:** `settings = Settings()` at the bottom — this creates a singleton that `main.py` imports.

**Imports from:** `os`, `dotenv`

**Imported by:** `agent/main.py`

---

### `agent/state.py` — Conversation Memory Schema

**What it does:** Defines a Python `TypedDict` (a dictionary with named, typed fields) called `AgentState`. This is the "shared memory" that all LangGraph nodes read from and write to.

Think of it as a whiteboard that every node in the conversation can look at and update:
- `messages`: the full chat history
- `current_flow`: "what mode are we in?" (greeting, verify, booking, etc.)
- `customer_verified`: has the caller proven who they are?
- `appointment_details`: partial booking info being collected

**Imports from:** `typing`, `langchain_core.messages`, `langgraph.graph.message`

**Imported by:** `graph_builder.py`, `nodes.py`

---

### `agent/nodes.py` — Conversation Handlers

**What it does:** This is the largest and most important file in the agent. It contains one function per "mode" the conversation can be in:

| Function | What it handles |
|----------|----------------|
| `greeting_node()` | The opening "Hello! Welcome to Epoxcel..." message |
| `verify_customer_node()` | Asks for phone number, checks SQLite via FastAPI |
| `registration_node()` | Collects name → phone → email for new customers |
| `faq_node()` | Uses ChromaDB to find the right FAQ answer |
| `appointment_node()` | Collects date + time, generates confirmation code |
| `complaint_node()` | Records the complaint via FastAPI ticket endpoint |
| `escalate_node()` | Creates escalation ticket, activates handoff mode |
| `general_chat_node()` | Free-form conversation using Groq LLM |
| `classify_intent()` | Helper: "Is this an FAQ, appointment, complaint, or chat?" |
| `classify_customer_type()` | Helper: "Is this a new or existing customer?" |
| `extract_phone_digits()` | Helper: Pulls 10-digit phone number from spoken text |
| `extract_appointment_info()` | Helper: Pulls date + time from natural speech |

**Imports from:** `state`, `handoff`, `chroma_client`, `langchain_openai`, `langchain_core`, `httpx`

**Imported by:** `graph_builder.py`

---

### `agent/graph_builder.py` — State Machine Assembler

**What it does:** Builds the LangGraph conversation graph by:
1. Creating a `StateGraph` and adding each node from `nodes.py`
2. Adding edges (the routing logic between nodes)
3. Adding conditional edges (routing functions that pick which node to go to next)
4. Compiling it with a `MemorySaver` (so the conversation memory persists across turns)
5. Wrapping the compiled graph in a `LangGraphLLM` class that LiveKit can treat as a regular LLM

**Key output:** `compiled_graph` — a global variable that `main.py` imports and uses for every call.

**Imports from:** `state`, `nodes`, `handoff`, `livekit.agents.llm`

**Imported by:** `agent/main.py`

---

### `agent/handoff.py` — Human Escalation Controller

**What it does:** Manages whether the AI should be "muted" (because a human agent has taken over).

Uses a simple Python dictionary (`_active_handoffs`) as an in-memory flag per session:
- `set_handoff_active(session_id, True)` → AI goes silent
- `is_handoff_active(session_id)` → checked before every LLM response
- Also syncs the handoff status to Supabase so the dashboard knows

**Imports from:** `database` (backend), `logging`, `os`

**Imported by:** `graph_builder.py`, `nodes.py`, `main.py`

---

### `agent/chroma_client.py` — Vector Database Connection

**What it does:** Opens (or creates) the ChromaDB persistent database in `agent/chroma_db/` and provides a `query_faq(text)` function that converts your question into a vector and finds the most similar FAQ document.

**Imports from:** `chromadb`, `chromadb.utils.embedding_functions`, `os`

**Imported by:** `nodes.py` (called inside `faq_node`), `main.py` (warm-up query)

---

### `agent/embed_documents.py` — One-Time FAQ Loader

**What it does:** Reads all `.txt` files from `agent/faq_docs/`, generates vector embeddings for each, and stores them in ChromaDB. You only need to run this once (or again whenever you add/edit FAQ files).

Run it with: `python embed_documents.py` from inside `agent/`

**Imports from:** `chroma_client`

**Imported by:** Nothing (run directly, not imported by anyone)

---

### `agent/utils.py` — Logging + Latency Tracking

**What it does:** Two things:
1. `setup_logging()` — configures Python's logging to write to both terminal and `logs/app.log` with rotating file support
2. `LatencyTracker` class — times each pipeline step (STT, LLM, TTS) to millisecond precision and saves to Supabase

**Imports from:** `os`, `time`, `logging`, `database` (lazy import inside class)

**Imported by:** `agent/main.py`, `backend/utils.py` (parallel file with same code)

---

### `backend/main.py` — FastAPI App Entry Point

**What it does:** Creates the FastAPI app, adds CORS middleware (so the React frontend can talk to it), registers all API routes, and initializes the SQLite database on first run.

Run it with: `uvicorn main:app --reload` from inside `backend/`

**Imports from:** `fastapi`, `routes`, `database`, `utils`

**Imported by:** Nothing — this is the top of the backend chain.

---

### `backend/routes.py` — All API Endpoints

**What it does:** Defines every REST API endpoint. Key ones:

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/api/token` | POST | Generates a LiveKit JWT token for a participant to join a room |
| `/api/rooms` | GET | Lists all active LiveKit rooms |
| `/api/rooms/active-sessions` | GET | Shows call sessions + auto-heals stale ones |
| `/api/rooms/{id}/transcript` | GET | Fetches full conversation transcript |
| `/api/customers` | POST | Registers a new customer in SQLite |
| `/api/customers/verify` | GET | Looks up a customer by phone number |
| `/api/tickets` | POST | Creates a support ticket (complaint or escalation) |
| `/health` | GET | System health check (SQLite + Supabase + env vars) |

**Imports from:** `database`, `fastapi`, `pydantic`, `livekit.api`

**Imported by:** `backend/main.py`

---

### `backend/database.py` — Data Access Layer

**What it does:** All database read/write operations in one place. Two databases:

**SQLite (local file):**
- `get_db_connection()` — opens the SQLite file
- `verify_customer_by_phone(phone)` — checks if customer exists
- `create_customer(name, phone, email)` — registers new customer
- `create_support_ticket(customer_id, category, description)` — logs a ticket

**Supabase (cloud PostgreSQL):**
- `create_call_session(...)` — starts a call record
- `complete_call_session(...)` — finalizes it with summary/duration
- `save_transcript_entry(...)` — saves one utterance
- `get_full_transcript(session_id)` — reads all utterances for a call
- `save_latency_log(...)` — saves one timing measurement

**Imports from:** `sqlite3`, `supabase`, `os`, `datetime`

**Imported by:** `backend/routes.py`, `agent/handoff.py`, `agent/utils.py`

---

### `backend/schema.sql` — Database Blueprint

**What it does:** SQL commands to create the three Supabase tables (`call_sessions`, `call_transcripts`, `latency_logs`). You paste this into the Supabase SQL editor once during setup.

Not a Python file — just SQL instructions.

---

### `frontend/src/livekit_client.js` — LiveKit JavaScript Wrapper

**What it does:** A JavaScript class (`LiveKitHelper`) that wraps the LiveKit client SDK. Handles:
- Connecting to a LiveKit room using a token
- Subscribing to audio tracks from the AI agent (so you can hear it)
- Managing microphone enable/disable
- Cleaning up audio elements when the call ends

**Imports from:** `livekit-client` (npm package)

**Imported by:** `frontend/src/App.jsx`

---

### `frontend/src/App.jsx` — Customer Web App

**What it does:** The React component that the customer sees. Manages:
- The "Join Room" screen (enter name, click start)
- Requesting an access token from FastAPI
- Calling `LiveKitHelper.connect()`
- The "Call Screen" with mic button, mute, hang up, and the pulsing orb visualizer
- Showing connection state and agent-speaking animations

**Imports from:** `react`, `livekit_client.js`, `JoinRoom` component, `CallScreen` component

**Imported by:** `frontend/src/index.js` (React entry point)

---

## 🔗 Import Dependency Chain

Here's how the files connect, in execution order when `python main.py dev` runs:

```
python agent/main.py dev
    │
    ├── config.py
    │       └── os, dotenv
    │
    ├── graph_builder.py
    │       ├── state.py
    │       │       └── typing, langchain_core, langgraph
    │       ├── nodes.py
    │       │       ├── state.py
    │       │       ├── handoff.py ──► backend/database.py ──► supabase, sqlite3
    │       │       └── chroma_client.py ──► chromadb
    │       └── handoff.py (same)
    │
    ├── backend/database.py  (via sys.path insertion)
    │       ├── supabase client
    │       └── sqlite3
    │
    ├── backend/utils.py
    │       └── logging, RotatingFileHandler
    │
    └── livekit plugins (silero VAD, deepgram STT/TTS)
```

---

*Next up → [02_PYTHON_FOUNDATIONS.md](./02_PYTHON_FOUNDATIONS.md)*
