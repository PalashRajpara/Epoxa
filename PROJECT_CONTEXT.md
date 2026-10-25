# Project Context: Epoxa — Voice AI Agent

> **Document Purpose:**  
> This file is a self-contained, comprehensive architectural and technical specification of the **Epoxa — Voice AI Agent** repository. It provides complete context on the codebase's past, present, and target architecture—including business logic, conversation state machines, WebRTC audio pipelines, REST APIs, database schemas, frontend clients, supervisor takeover mechanics, security boundaries, and critical engineering nuances. It is designed to be fed into any AI model to provide instant, full context.

---

## Table of Contents
1. [Executive Summary & Product Identity](#1-executive-summary--product-identity)
2. [Architectural Evolution (Current vs Target State)](#2-architectural-evolution-current-vs-target-state)
3. [End-to-End System Architecture & Data Flow](#3-end-to-end-system-architecture--data-flow)
4. [Complete Technology Stack & Dependencies](#4-complete-technology-stack--dependencies)
5. [Repository Directory & Complete File Map](#5-repository-directory--complete-file-map)
6. [The Real-Time Voice Pipeline (LiveKit RTC)](#6-the-real-time-voice-pipeline-livekit-rtc)
7. [Conversational State Machine (LangGraph Deep Dive)](#7-conversational-state-machine-langgraph-deep-dive)
8. [Human Supervisor Takeover & Audio Isolation Protocol](#8-human-supervisor-takeover--audio-isolation-protocol)
9. [Authentication, Authorization & Security Architecture](#9-authentication-authorization--security-architecture)
10. [Backend REST API Reference](#10-backend-rest-api-reference)
11. [Database Persistence Layer & Schema Specifications](#11-database-persistence-layer--schema-specifications)
12. [Frontend Applications Architecture](#12-frontend-applications-architecture)
13. [Performance Optimizations & Latency Telemetry](#13-performance-optimizations--latency-telemetry)
14. [Critical Engineering Nuances & Hard-Earned Bug Fixes](#14-critical-engineering-nuances--hard-earned-bug-fixes)
15. [Environment Configuration & Operational Run Guide](#15-environment-configuration--operational-run-guide)
16. [Technical Debt Register & Refactoring Roadmap](#16-technical-debt-register--refactoring-roadmap)

---

## 1. Executive Summary & Product Identity

### 1.1 What is Epoxa?
**Epoxa — Voice AI Agent** is an enterprise-grade, real-time AI customer support system. It enables low-latency, natural, spoken conversations directly through a web browser between human callers and an AI voice agent named **"Epixa"**, representing a business named **"Epoxcel"**.

### 1.2 Core Business Capabilities
1. **Full-Duplex Natural Voice Conversation**: Under ~1.0s end-to-end turn latency with real-time speech boundary detection, user interruption support, and streaming audio synthesis.
2. **Stateful Multi-Turn Dialog Management**: Managed via **LangGraph**, handling:
   - Account identity verification via 10-digit phone number.
   - Self-service customer onboarding and profile registration.
   - Natural appointment booking with conversational date/time extraction and confirmation codes.
   - Customer complaint logging with automatic support ticket creation.
   - Grounded RAG-based FAQ assistance (retrieving hours, locations, pricing, refund policies).
3. **Supervisor Command Center & Live Takeover**:
   - Real-time active call monitoring and live transcript streaming.
   - One-click human agent voice takeover.
   - Intelligent multi-participant audio track isolation (AI agent automatically stops listening and speaking to human agents).
   - Graceful hand-back from human agent to AI with automatic re-greeting.
4. **Reliable Persistence Layer**:
   - Historical dual persistence: Local **SQLite** (`backend/voice_support.db`) + Cloud **Supabase PostgreSQL**.
   - Target unified persistence: Dedicated fresh **Supabase PostgreSQL** database versioned strictly via **Alembic + SQLAlchemy**.
   - Frontends **never** query database tables directly; all access is mediated by the FastAPI backend.

### 1.3 Identity & Branding Boundaries
- **Product Name:** `Epoxa — Voice AI Agent`
- **Voice Agent Persona:** `Epixa`
- **Represented Company:** `Epoxcel`
- Note: The persona and company names are intentionally distinct from the product name to preserve conversational behavior and prompt context.

---

## 2. Architectural Evolution (Current vs Target State)

### 2.1 Current Implementation State (Legacy Baseline)
- **FastAPI Backend:** Handles JWT token minting (`POST /api/token`), customer verification, ticket logging, and room session listing (`GET /api/rooms/active-sessions`).
- **LiveKit Agent Worker:** Standalone Python process connecting to LiveKit Cloud. Employs Silero VAD, Deepgram Nova-2 STT, Groq Llama 3.1 LLM, Deepgram Aura TTS, ChromaDB vector store, and LangGraph StateGraph.
- **Persistent Anti-Patterns:**
  - `agent/main.py` directly executes `sys.path.insert(0, BACKEND_DIR)` to import `backend/database.py`, but calls the backend over HTTP (`httpx`) for customer verification and tickets.
  - `backend/routes.py` has an unauthenticated `POST /api/token` endpoint that allows any caller to pass `role: "agent"` and receive a privileged 2-hour supervisor token.
  - `backend/database.py` and `agent/utils.py` duplicate ~180 lines of logging and latency code.
  - Appointment booking collects conversational details and produces an `APT-XXXX` confirmation code, but never saves the appointment to any database table.
  - Volatile supervisor takeover state is stored in an in-memory dictionary `_active_handoffs = {}` in the agent worker.

### 2.2 Production Architecture (Completed Epoxa Monorepo)
- **Monorepo Layout:**
  - `packages/core` (`epoxa_core`): Models, repositories, domain services (`AppointmentService`, `CustomerService`, `CallSessionService`, `TicketService`, `KBService`), Unit of Work, typed settings (`pydantic-settings`), structured JSON logging.
  - `packages/api-client` (`@epoxa/api-client`): Generated TypeScript API client matching FastAPI schemas.
  - `packages/ui-tokens` (`@epoxa/ui-tokens`): Extracted CSS design tokens, glassmorphism surfaces, and orb animation keyframes.
  - `apps/api` (`epoxa_api`): FastAPI REST & real-time SSE service with Supabase JWKS verification, RBAC, advisory-locked reconciliation and retention jobs.
  - `apps/agent` (`epoxa_agent`): LiveKit Voice Agent worker with LangGraph dialogue nodes, bounded off-hot-path persistence queue, and strict audio isolation.
  - `apps/web` (`epoxa-web`): Customer voice application built with Vite + React 18 + TS.
  - `apps/dashboard` (`epoxa-dashboard`): Supervisor operations console built with Vite + React 18 + TS.
- **Supervisor Authentication via Supabase Auth:**
  - Dashboard supervisors authenticate with Supabase Auth. FastAPI verifies JWTs via asymmetric JWKS.
  - LiveKit takeover token generation is strictly guarded by supervisor authentication.
  - Public callers use rate-limited `POST /api/v1/calls` with unguessable room names and audio-only tokens.
- **Dedicated Supabase PostgreSQL Schema:**
  - 12 normalized tables versioned via Alembic migrations with naming conventions and DB triggers.
  - Row Level Security (RLS) forced across all tables; access from `anon` and `authenticated` revoked.
  - Least-privilege database roles: `epoxa_api` and `epoxa_agent`.
  - pgvector semantic search with HNSW cosine index for stateless knowledge base retrieval.

---

## 3. End-to-End System Architecture & Data Flow

```
                                  ┌────────────────────────────────┐
                                  │       LiveKit Cloud RTC        │
                                  │   (WebRTC Audio, Tracks, Data) │
                                  └───────┬──────────────┬─────────┘
                                          │              │
                   ┌──────────────────────┘              └─────────────────────┐
                   ▼                                                           ▼
       ┌────────────────────────┐                                  ┌────────────────────────┐
       │   Customer Web App     │                                  │  Supervisor Dashboard  │
       │   (React.js @ :3000)   │                                  │   (React.js @ :3001)   │
       │ ────────────────────── │                                  │ ────────────────────── │
       │ • WebRTC Audio Stream  │                                  │ • Supabase Auth Login  │
       │ • Glowing Orb State UI │                                  │ • Active Calls Polling │
       │ • Public Token Request │                                  │ • Live Transcript Stream│
       │   (Role: "customer")   │                                  │ • Live Audio Takeover  │
       │ • Call Duration Timer  │                                  │ • Hand-back to AI data │
       └───────────┬────────────┘                                  └───────────┬────────────┘
                   │                                                           │
                   │ Public Token & Customer Requests                          │ Authenticated (Bearer <JWT>)
                   ▼                                                           ▼
       ┌────────────────────────────────────────────────────────────────────────────────────┐
       │                       FastAPI Application Server (`epoxa_api`)                     │
       │ ────────────────────────────────────────────────────────────────────────────────── │
       │ • Supervisor Auth Guard: Validates Supabase JWTs & enforces supervisor role        │
       │ • Token Minting: Guarded for `agent`, public for `customer`                        │
       │ • Services: Customer, Appointment, Ticket, Session, and Room Reconciliation        │
       │ • Strictly Bounded Request/Response Schemas (Pydantic v2)                          │
       │ • Structured JSON Logging & Request Correlation Middleware                         │
       └────────────────────────────────────────┬───────────────────────────────────────────┘
                                                │
                                                ▼
       ┌────────────────────────────────────────────────────────────────────────────────────┐
       │                          Shared Core Library (`epoxa_core`)                        │
       │ ────────────────────────────────────────────────────────────────────────────────── │
       │ • Domain Entities, Invariants, and Business Exceptions                             │
       │ • SQLAlchemy Repositories: Customers, Appointments, Tickets, Sessions, Transcripts │
       │ • Central Typed Settings (`pydantic-settings` reading validated .env)               │
       │ • Connection Pool & Session Management (SQLAlchemy Engine)                         │
       └─────────────────────────────┬───────────────────────────┬──────────────────────────┘
                                     │                           │
                                     ▼                           ▼
       ┌─────────────────────────────────────────┐   ┌──────────────────────────────────────┐
       │        PostgreSQL Database              │   │      LiveKit Voice Agent Worker      │
       │   (Dedicated Epoxa Supabase Project)    │   │           (`epoxa_agent`)            │
       │ ─────────────────────────────────────── │   │ ──────────────────────────────────── │
       │ • Versioned with Alembic Migrations     │   │ • Silero VAD (Interruption)          │
       │ • Tables: supervisors, customers,       │   │ • Deepgram Nova-2 STT                │
       │   appointments, tickets, call_sessions, │   │ • LangGraph State Machine            │
       │   call_transcripts, latency_logs,       │   │ • ChromaDB RAG FAQ Retrieval         │
       │   handoff_events                        │   │ • Groq Llama 3.1 LLM                 │
       │ • Defense-in-Depth RLS Enabled          │   │ • Deepgram Streaming TTS             │
       │ • Indexed Query Patterns                │   │ • Multi-Participant Audio Isolation  │
       └─────────────────────────────────────────┘   └──────────────────────────────────────┘
```

---

## 4. Complete Technology Stack & Dependencies

| Layer | Technology | Library / Model | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **RTC Media Transport** | LiveKit Cloud | `livekit`, `livekit-agents` (Python 0.12+), `livekit-client` (JS 2.5+) | WebRTC audio streaming, room session events, data packet communication |
| **Voice Activity Detection** | Silero VAD | `livekit-plugins-silero` | Low-latency voice detection, speech start/stop boundaries, user interruption |
| **Speech-to-Text (STT)** | Deepgram Nova-2 | `livekit-plugins-deepgram` | Streaming voice-to-text audio transcription |
| **Text-to-Speech (TTS)** | Deepgram Aura | `deepgram.TTS(model="aura-asteria-en", use_streaming=True)` | High-quality, low-latency streaming audio voice generation |
| **LLM Reasoning Engine** | Groq Cloud | `llama-3.1-8b-instant` via `langchain-openai` | Ultra-fast conversational generation (<300ms time-to-first-token) |
| **State Orchestration** | LangGraph | `langgraph`, `langchain-core` | Cyclic state graph with `MemorySaver` in-memory checkpointing per session |
| **Vector DB & Embeddings**| ChromaDB | `chromadb`, `sentence-transformers` (`all-MiniLM-L6-v2`) | Local persistent vector storage for semantic search over business FAQs |
| **Backend Framework** | FastAPI | `fastapi`, `uvicorn`, `pydantic` | Async REST API server, room controller, JWT minter |
| **Database ORM & Migrations**| SQLAlchemy + Alembic | `sqlalchemy>=2.0`, `alembic>=1.13` | Typed ORM models, connection pooling, version-controlled migrations |
| **Database Engine** | PostgreSQL | Supabase Dedicated Project | Centralized durable storage for all application entities |
| **Authentication Authority**| Supabase Auth | `@supabase/supabase-js`, `PyJWT` | Supervisor authentication, JWT minting, password recovery, session refresh |
| **Customer Web App** | React | React 18, `livekit-client`, `lucide-react` | Customer browser UI with pulsing voice orb and call controls |
| **Admin Dashboard** | React | React 18, `livekit-client`, `@supabase/supabase-js`, `lucide-react` | Protected supervisor monitoring console with audio takeover & transcripts |

---

## 5. Repository Directory & Complete File Map

```
voice-ai-agent/ (Epoxa)
├── .env.example                         # Safe configuration template (placeholders only)
├── .env                                 # Active credentials & API keys (Git ignored)
├── .gitignore                           # Excludes secrets, databases, logs, virtual environments
├── start.sh                             # Multi-process development launcher (tmux support)
├── README.md                            # High-level overview and setup guide
├── PROJECT_CONTEXT.md                   # This master document
├── alembic.ini                          # Alembic migration configuration
│
├── core/                                # SHARED CORE PACKAGE (`epoxa_core`)
│   ├── config.py                        # Pydantic Settings (environment loading & validation)
│   ├── logging.py                       # Unified structured rotating logger (console + logs/app.log)
│   ├── database.py                      # SQLAlchemy engine, sessionmaker, and DB dependencies
│   ├── models/                          # SQLAlchemy ORM Models & Domain Schemas
│   │   ├── base.py                      # Declarative Base and timestamp mixins
│   │   ├── supervisor.py                # Supervisor profile mapping to auth.users
│   │   ├── customer.py                  # Customer profiles
│   │   ├── appointment.py               # Persisted appointment bookings
│   │   ├── ticket.py                    # Support tickets & escalations
│   │   ├── session.py                   # Call session records
│   │   ├── transcript.py                # Utterance transcript turns
│   │   ├── latency.py                   # Step latency measurements
│   │   └── handoff.py                   # Supervisor takeover audit events
│   └── repositories/                    # Clean Repository Pattern Implementations
│       ├── supervisor_repo.py
│       ├── customer_repo.py
│       ├── appointment_repo.py
│       ├── ticket_repo.py
│       └── session_repo.py
│
├── backend/                             # FASTAPI REST API SERVICE (`epoxa_api`)
│   ├── main.py                          # Lifespan manager, CORS middleware, router registration
│   ├── dependencies/
│   │   ├── auth.py                      # Supabase JWT token verification guard
│   │   └── db.py                        # Database session dependency injection
│   ├── routes/
│   │   ├── auth.py                      # Token minting (/api/v1/tokens) with role guards
│   │   ├── customers.py                 # Customer listing, phone verification, registration
│   │   ├── appointments.py              # Appointment scheduling endpoints
│   │   ├── tickets.py                   # Support ticket creation and retrieval
│   │   ├── rooms.py                     # LiveKit room controls & active sessions
│   │   └── health.py                    # Liveness (/health/live) and readiness (/health/ready)
│   ├── schemas/                         # Pydantic v2 DTOs (Request/Response models with bounds)
│   └── utils.py                         # Route helpers and logging setup
│
├── agent/                               # LIVEKIT PYTHON VOICE AGENT WORKER (`epoxa_agent`)
│   ├── main.py                          # LiveKit entrypoint, VAD, STT, TTS, room listeners, timeout
│   ├── graph_builder.py                 # LangGraph StateGraph & custom LangGraphLLM wrapper
│   ├── nodes/                           # Modular Dialogue Graph Nodes
│   │   ├── router.py                    # Fast-path regex & intent classification
│   │   ├── greeting.py                  # Initial greeting node
│   │   ├── verify.py                    # Customer phone verification node
│   │   ├── registration.py              # Step-by-step customer onboarding node
│   │   ├── appointment.py               # Appointment booking with DB persistence
│   │   ├── complaint.py                 # Customer grievance ticket creation node
│   │   ├── faq.py                       # ChromaDB RAG FAQ answerer node
│   │   ├── escalate.py                  # Human escalation node
│   │   └── chat.py                      # General conversational chat fallback node
│   ├── handoff.py                       # Supervisor takeover tracker & audio track unsubscription
│   ├── chroma_client.py                 # ChromaDB client initialization & vector search
│   ├── embed_documents.py               # Ingestion script indexing FAQ files into ChromaDB
│   ├── config.py                        # Agent environment validation
│   ├── utils.py                         # LatencyTracker and timing helpers
│   └── faq_docs/                        # Grounded Knowledge Base Text Files
│       ├── hours.txt                    # Operating hours and holiday policies
│       ├── location.txt                 # Office addresses and parking information
│       ├── pricing.txt                  # Service tiers, membership, and hourly rates
│       └── refunds.txt                  # Cancellation terms and refund policies
│
├── migrations/                          # ALEMBIC VERSION CONTROL
│   ├── env.py                           # Dynamic database URL loader & target metadata
│   ├── script.py.mako                   # Migration template
│   └── versions/
│       └── 0001_initial_schema.py       # Full PostgreSQL 8-table migration revision
│
├── frontend/                            # CUSTOMER REACT APP (Port 3000)
│   ├── package.json                     # React 18, livekit-client, lucide-react
│   └── src/
│       ├── App.jsx                      # App container, call state machine, screen switching
│       ├── livekit_client.js            # LiveKitHelper WebRTC client wrapper
│       ├── design-system.css            # Dark mode glassmorphism styling
│       └── components/
│           ├── JoinRoom.jsx             # Pre-call form (Name & Room ID input)
│           ├── CallScreen.jsx           # Active call UI (glowing voice orb visualizer, timer, mute)
│           ├── ConnectionStatus.jsx     # Connection indicator pill
│           └── MicButton.jsx            # Interactive mic toggle button
│
├── dashboard/                           # SUPERVISOR REACT DASHBOARD (Port 3001)
│   ├── package.json                     # React 18, livekit-client, @supabase/supabase-js
│   └── src/
│       ├── App.jsx                      # Supervisor layout, auth session check, call selector
│       ├── design-system.css            # Dark SaaS dashboard styling
│       └── components/
│           ├── LoginScreen.jsx          # Supabase Auth supervisor sign-in form
│           ├── ActiveCallsList.jsx      # Auto-polling active/historical calls list with status pills
│           ├── TranscriptView.jsx       # Real-time message-by-message conversation bubble view
│           └── JoinCallButton.jsx       # Live audio takeover, mute controls, and "Hand back to AI"
│
├── tests/                               # AUTOMATED TEST SUITE
│   ├── conftest.py                      # Pytest fixtures, mock LiveKit, test database engine
│   ├── unit/                            # Domain models, Pydantic schemas, routing rules
│   ├── integration/                     # FastAPI route integration tests via TestClient
│   └── agent/                           # Mock voice pipeline & state graph transition tests
│
├── docs/                                # DOCUMENTATION & SPECIFICATIONS
│   ├── audit_report.md                  # Phase A Repository Audit
│   ├── architecture_proposal.md         # Phase B Initial Proposal
│   ├── database/schema_design.md        # Complete 8-Table Database Specification
│   └── architecture/overview.md         # Complete Architecture Overview
│
└── logs/                                # SYSTEM LOGS
    └── app.log                          # Rotating log output file (5MB, 3 backups)
```

---

## 6. The Real-Time Voice Pipeline (LiveKit RTC)

### 6.1 Audio Flow Breakdown
```
[Customer Speaks into Mic]
        │
        ▼
[Silero VAD] ──────────► Detects speech start/stop boundaries
        │
        ▼
[Deepgram Nova-2 STT] ─► Real-time voice-to-text audio transcription
        │
        ▼
[Custom LangGraphLLM] ─► Maps to LangChain, runs StateGraph, yields AIMessage
        │
        ▼
[Deepgram Aura TTS] ───► Streams synthesized audio (`aura-asteria-en`)
        │
        ▼
[Customer Hears Epixa's Voice via Browser Speaker]
```

### 6.2 Voice Pipeline Agent Settings (`agent/main.py`)
- **VAD Plugin:** `silero.VAD.load()` (Pre-warmed at module startup to eliminate cold start).
- **STT Plugin:** `deepgram.STT(api_key=...)`.
- **TTS Plugin:** `deepgram.TTS(api_key=..., model="aura-asteria-en", use_streaming=True)`.
- **Pipeline Timing Parameters:**
  - `interrupt_speech_duration = 0.7`: Number of seconds user must speak before interrupting the agent.
  - `interrupt_min_words = 2`: Minimum word count required to trigger interruption (prevents coughs/breathing from cutting off Epixa).
  - `min_endpointing_delay = 0.6`: Wait time after user stops speaking before finalizing the utterance.
  - `preemptive_synthesis = False`: Disabled to allow LangGraph custom state execution to complete cleanly without orphaned audio chunks.

### 6.3 Custom LiveKit LangGraph LLM Adapter (`agent/graph_builder.py`)
Because LiveKit's `VoicePipelineAgent` expects an instance of `livekit.agents.llm.LLM`, a custom bridge class is implemented:
- `LangGraphLLM(llm.LLM)`: Accepts the compiled StateGraph and `session_id` (used as LangGraph `thread_id`).
- `LangGraphStream(llm.LLMStream)`: Implements `_run()`:
  1. Checks if handoff is active via `is_handoff_active(session_id)`. If active, exits immediately, keeping the AI silent.
  2. Converts LiveKit `ChatContext` into LangChain message types (`SystemMessage`, `HumanMessage`, `AIMessage`).
  3. Executes `await graph.ainvoke({"messages": lc_messages}, config={"configurable": {"thread_id": thread_id}})`.
  4. Extracts the resulting `AIMessage` and sends it to LiveKit's event channel chunk-by-chunk via `self._event_ch.send_nowait(chunk)`.

---

## 7. Conversational State Machine (LangGraph Deep Dive)

The dialogue state machine is built with **LangGraph** (`agent/graph_builder.py` and `agent/nodes/`) and persists state turn-by-turn with `MemorySaver`.

### 7.1 State Schema (`AgentState` in `agent/state.py`)
```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # Chat history across turns
    customer_verified: bool                               # True if phone verified
    customer_info: Optional[Dict[str, Any]]               # Loaded customer profile
    verification_attempts: int                            # Counter (escalates after 3 failures)
    appointment_details: Optional[Dict[str, Any]]         # {"date": str, "time": str, "confirmation_code": str}
    complaint_details: Optional[Dict[str, Any]]           # {"description": str, "ticket_id": int}
    target_flow: Optional[str]                            # Deferred target flow (e.g., 'booking', 'complaint')
    current_flow: str                                     # 'greeting', 'verify', 'registration', 'faq', 'booking', 'complaint', 'escalation', 'chat', 'idle'
    registration_step: Optional[str]                      # 'name' -> 'phone' -> 'email' -> 'done'
    reg_name: Optional[str]
    reg_phone: Optional[str]
    reg_email: Optional[str]
```

### 7.2 StateGraph Flowchart
```
                          [ START ]
                              │
                      (entry_router)
                      ┌───────┴───────┐
                 (No input)      (User spoke)
                      │               │
                      ▼               ▼
                [ greeting ]   [ route_input ]
                      │        (router_node)
                      ▼               │
                   [ END ]            ├──────────────────────┬──────────────────────┬────────────────────┐
                                      ▼                      ▼                      ▼                    ▼
                             [ verify_customer ]      [ registration ]            [ faq ]         [ general_chat ]
                                      │                      │                      │                    │
                                      ▼                      ▼                      ▼                    ▼
                                   [ END ]                [ END ]                [ END ]              [ END ]
                                      ▲                      ▲                      ▲
                                      │ (If unverified)      │                      │
                                      ├──────────────────────┴──────────────────────┘
                                      │
                                      ├──────────────────────┬──────────────────────┐
                                      ▼                      ▼                      ▼
                               [ appointment ]         [ complaint ]           [ escalate ]
                                      │                      │                      │
                                      ▼                      ▼                      ▼
                                   [ END ]                [ END ]                [ END ]
```

### 7.3 Routing & Flow Preservation Logic (`router_node`)
1. **Word-Boundary Escalation Fast-Path**:
   Checks user speech against regex:
   `\b(speak to a? human|talk to a? human|transfer me|speak to a? (representative|agent|supervisor|manager)|handover|connect me to a? human)\b`
   If matched, immediately routes to `escalate` without wasting LLM tokens or latency.
2. **Active Flow Preservation**:
   If `current_flow` is already `"verify"`, `"registration"`, `"booking"`, or `"complaint"`, the router skips intent classification entirely. This prevents Groq LLM latency overhead (saving 1.2–2.0 seconds) and prevents dialog drift mid-task.
3. **Intent Classification Fallback**:
   If idle, uses fast Groq LLM (`temperature=0.0`) to classify the utterance into:
   - `appointment`: If customer is unverified, sets `target_flow="booking"` and routes to `verify`. If verified, routes directly to `appointment`.
   - `complaint`: If customer is unverified, sets `target_flow="complaint"` and routes to `verify`. If verified, routes directly to `complaint`.
   - `faq`: Routes directly to `faq` (RAG search).
   - `escalate`: Routes to `escalate`.
   - `chat`: Routes to `general_chat`.

### 7.4 Detailed Node Behaviors
- **`greeting_node`**: Welcomes the caller: *"Hello! Welcome to Epoxcel. My name is Epixa. How can I help you today?"*
- **`verify_customer_node`**:
  - Turn 1: Inquires whether the caller is existing or new.
  - Extracts 10-digit phone number using `extract_phone_digits()`.
  - Queries `GET /api/v1/customers/verify?phone={phone}`.
  - On success: Marks `customer_verified=True`, stores profile in `customer_info`, and transitions to `target_flow`.
  - On failure: Increments `verification_attempts`. After 3 failed attempts, routes to `escalate_node`.
- **`registration_node`**:
  - Implements a state-machine step sequence:
    1. `step=None` or `'name'`: Asks for full name.
    2. `step='name'`: Stores name, requests 10-digit phone number.
    3. `step='phone'`: Validates digits, requests email address.
    4. `step='email'`: Calls `POST /api/v1/customers` to persist profile. Marks customer as verified and returns to general assistance.
- **`appointment_node`**:
  - Prompts for appointment date and time.
  - Uses `extract_appointment_info()` (fast LLM returning JSON `{"date": "...", "time": "..."}`).
  - Prompts for missing fields if only one was provided.
  - Once both are collected, asks for confirmation: *"Just to confirm, you'd like to schedule your appointment for Friday at 2 PM. Is that correct?"*
  - On affirmative response, generates confirmation code (e.g., `APT-8421`), persists the appointment in the database, and marks appointment booked.
- **`complaint_node`**:
  - Prompts caller to describe grievance.
  - Submits payload to `POST /api/v1/tickets` with `category="Complaint"` and customer ID.
  - Returns generated Ticket ID to the customer.
- **`faq_node` (RAG Retrieval)**:
  - Takes user query and searches ChromaDB via `query_faq(user_query, n_results=1)`.
  - Retrieves matched context chunk from indexed files (`hours.txt`, `location.txt`, `pricing.txt`, `refunds.txt`).
  - Instructs Groq LLM to generate a natural, conversational response strictly grounded in the retrieved text.
- **`escalate_node`**:
  - Automatically files an Escalation ticket via `POST /api/v1/tickets`.
  - Sets global handoff flag `set_handoff_active(session_id, True)`.
  - Informs caller: *"I am transferring you to a human agent now. A representative will join this call shortly. Please hold."*
- **`general_chat_node`**:
  - Handles greetings, small talk, gratitude, and mic checks (*"Am I audible?"* -> *"Yes, I can hear you loud and clear!"*).
  - Includes local deterministic fallback responses if the LLM call times out.

---

## 8. Human Supervisor Takeover & Audio Isolation Protocol

```
       Customer Web App                          AI Voice Agent                           Supervisor Dashboard
       ────────────────                          ──────────────                           ────────────────────
              │                                         │                                           │
       [Customer Speaks]                                │                                           │
       "Transfer me to a human"                         │                                           │
              │                                         │                                           │
              ├────────────────────────────────────────►│                                           │
              │                                   (Escalates)                                       │
              │                                   Mutes AI worker                                   │
              │                                   Creates Ticket                                    │
              │◄────────────────────────────────────────┤                                           │
              │  "Transferring to human agent..."       │                                           │
              │                                         │                                    (Active Call List)
              │                                         │                                    Sees status "escalated"
              │                                         │                                           │
              │                                         │                                    Clicks "Join Live Call"
              │                                         │                                           │
              │◄────────────────────────────────────────┼───────────────────────────────────────────┤
              │            Human Agent and Customer Speak Directly (WebRTC)                         │
              │                                         │                                           │
              │                                   (AI Ignores                                       │
              │                                    Supervisor)                                      │
              │                                         │                                           │
              │                                         │                                    Clicks "Hand back to AI"
              │                                         │◄──────────────────────────────────────────┤
              │                                         │  DataPacket: { "action": "resume" }       │
              │                                         │                                           │
              │                                   Unmutes AI worker                                 │
              │◄────────────────────────────────────────┤                                           │
              │  "Welcome back! I'm back on the line..."│                                           │
```

### 8.1 Audio Track Isolation
1. **Identity Tagging:**
   - Supervisors receive tokens with identity: `agent_<uuid>` or `human_<uuid>`.
   - Callers receive tokens with identity: `customer_<uuid>`.
2. **AI Track Filtering (`agent/main.py`):**
   ```python
   @ctx.room.on("track_published")
   def on_track_published(publication, participant):
       if participant.identity.startswith("agent_") or participant.identity.startswith("human_"):
           logger.info(f"[Handoff] Ignoring track from supervisor: {participant.identity}")
           publication.set_subscribed(False)  # AI physically unsubscribes from supervisor audio
   ```
3. **Data Packet Resume Signal:**
   - Supervisor dashboard sends reliable LiveKit DataPacket: `{ "action": "resume" }`.
   - The AI agent catches the packet, clears handoff mode, and speaks: *"Welcome back! I'm back on the line. How can I help you resolve the rest of your issue?"*

---

## 9. Authentication, Authorization & Security Architecture

### 9.1 Supervisor Authentication (Supabase Auth)
- The React supervisor dashboard uses `@supabase/supabase-js` solely for identity operations (`signInWithPassword`, `signOut`, session refresh).
- Once logged in, the dashboard attaches the JWT:
  `Authorization: Bearer <access_token>`
  to all requests sent to the FastAPI backend.
- FastAPI has a dependency `get_current_supervisor`:
  1. Extracts the Bearer token.
  2. Verifies the JWT signature using the Supabase JWT secret (`SUPABASE_JWT_SECRET`) or Supabase public key / user endpoint.
  3. Verifies that the user exists in `supervisors` table and has `is_active = True`.
  4. Injects the `Supervisor` model into the route handler.
- If unauthenticated or token is expired -> `401 Unauthorized`.
- If user is not an active supervisor -> `403 Forbidden`.

### 9.2 Token Generation Security (`POST /api/v1/tokens`)
- Requesting `role: "agent"` requires `get_current_supervisor` dependency.
- Requesting `role: "customer"` is public (for the customer web app) and issues a short-lived (10 min) customer token with identity `customer_<uuid>`.
- Any unauthenticated request attempting to pass `role: "agent"` is rejected with `401/403`.

### 9.3 Public Customer Protection
- Public customer interaction is limited to token generation for voice rooms, phone number verification against their own phone, and submitting complaints.
- All customer endpoints enforce strict Pydantic character limits and input sanitization.
- Public customer endpoints never expose supervisor credentials or unrestricted records.

---

## 10. Backend REST API Reference

All endpoints are versioned under `/api/v1/` on port `8000`.

| Method | Endpoint | Access Level | Purpose | Request Body / Query | Response Details |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/health/live` | Public | Liveness probe ping | None | `{"status": "ok"}` |
| **GET** | `/health/ready` | Public (Sanitized) | Readiness probe (DB connectivity) | None | `{"status": "ready", "database": "connected"}` |
| **POST** | `/api/v1/tokens` | Mixed | Mints LiveKit JWT token | `{ "room_name": str, "participant_name": str, "role": "customer" \| "agent" }` | `{"token": str, "identity": str, "server_url": str}` |
| **GET** | `/api/v1/rooms` | Supervisor | Lists active LiveKit rooms from cloud | None | `{"rooms": [{"sid": str, "name": str, ...}]}` |
| **POST** | `/api/v1/rooms` | Supervisor | Pre-creates a LiveKit room | `{ "name": str, "empty_timeout": int, "max_participants": int }` | Room metadata object |
| **GET** | `/api/v1/rooms/active-sessions` | Supervisor | Lists active & historical calls with pagination | `?limit=50&offset=0` | `{"sessions": [...], "total": int}` |
| **GET** | `/api/v1/rooms/{session_id}/transcript` | Supervisor | Conversation transcript for session | `?limit=100&offset=0` | `{"transcript": [...], "status": str}` |
| **POST** | `/api/v1/rooms/end-session` | Supervisor | Manually terminates call session | `{ "session_id": str, "room_name": str }` | `{"success": true}` |
| **GET** | `/api/v1/customers` | Supervisor | Lists customer directory | `?limit=50&offset=0` | `{"customers": [...], "total": int}` |
| **GET** | `/api/v1/customers/verify` | Public / Agent | Verify caller by 10-digit phone | `?phone=1234567890` | `{"verified": true, "customer": {...}}` |
| **POST** | `/api/v1/customers` | Public / Agent | Onboard new customer profile | `{ "name": str, "phone": str, "email": str }` | Customer record object |
| **GET** | `/api/v1/appointments` | Supervisor | Lists scheduled appointments | `?date=YYYY-MM-DD` | `{"appointments": [...]}` |
| **POST** | `/api/v1/appointments` | Public / Agent | Confirms appointment booking | `{ "customer_id": uuid, "date": str, "time": str }` | `{"confirmation_code": str, ...}` |
| **GET** | `/api/v1/tickets` | Supervisor | Lists support grievances & escalations | `?status=open` | `{"tickets": [...]}` |
| **POST** | `/api/v1/tickets` | Public / Agent | Creates support ticket | `{ "customer_id": uuid, "category": str, "description": str }` | `{"ticket_id": int, ...}` |

---

## 11. Database Persistence Layer & Schema Specifications

### 11.1 The 8-Table Target PostgreSQL Schema

```mermaid
erDiagram
    auth_users ||--o| supervisors : "profile"
    supervisors ||--o{ tickets : "assigned to"
    supervisors ||--o{ handoff_events : "initiated by"
    
    customers ||--o{ appointments : "books"
    customers ||--o{ tickets : "raises"
    customers ||--o{ call_sessions : "participates in"
    
    call_sessions ||--o{ call_transcripts : "contains"
    call_sessions ||--o{ latency_logs : "records"
    call_sessions ||--o{ handoff_events : "escalates through"
    call_sessions ||--o{ tickets : "originates"
```

#### Table 1: `supervisors`
Maps authenticated human agents from Supabase Auth (`auth.users`) to application roles.
- `id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE`
- `email VARCHAR(255) NOT NULL UNIQUE`
- `full_name VARCHAR(100) NOT NULL`
- `role VARCHAR(50) NOT NULL DEFAULT 'supervisor' CHECK (role IN ('supervisor', 'admin'))`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Table 2: `customers`
Customer profiles for identification and call history.
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `name VARCHAR(200) NOT NULL`
- `phone VARCHAR(20) NOT NULL UNIQUE` (10–15 normalized digits)
- `email VARCHAR(255)`
- `status VARCHAR(50) NOT NULL DEFAULT 'Standard' CHECK (status IN ('Standard', 'Premium', 'Basic', 'VIP'))`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Table 3: `appointments`
Persists confirmed appointments. **(Fixes the legacy defect where bookings were only mock codes).**
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `customer_id UUID REFERENCES customers(id) ON DELETE SET NULL`
- `appointment_date DATE NOT NULL`
- `appointment_time VARCHAR(50) NOT NULL` (e.g. `'2:00 PM'`)
- `confirmation_code VARCHAR(32) NOT NULL UNIQUE` (e.g. `'APT-8421'`)
- `status VARCHAR(50) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled', 'completed', 'rescheduled'))`
- `notes TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Table 4: `tickets`
Support grievances and escalations with human-readable integer IDs.
- `id SERIAL PRIMARY KEY`
- `customer_id UUID REFERENCES customers(id) ON DELETE SET NULL`
- `session_id UUID REFERENCES call_sessions(id) ON DELETE SET NULL`
- `category VARCHAR(100) NOT NULL CHECK (category IN ('Complaint', 'Escalation', 'Billing', 'General', 'Technical'))`
- `description TEXT NOT NULL` (max 2,000 characters)
- `status VARCHAR(50) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in-progress', 'resolved', 'closed'))`
- `assigned_supervisor_id UUID REFERENCES supervisors(id) ON DELETE SET NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Table 5: `call_sessions`
Full lifecycle record for each LiveKit voice call session.
- `id UUID PRIMARY KEY`
- `room_name VARCHAR(128) NOT NULL`
- `room_sid VARCHAR(128)`
- `participant_name VARCHAR(200)`
- `customer_id UUID REFERENCES customers(id) ON DELETE SET NULL`
- `started_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `ended_at TIMESTAMPTZ`
- `duration_seconds INTEGER DEFAULT 0 CHECK (duration_seconds >= 0)`
- `status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'escalated', 'completed', 'dropped', 'timeout', 'error'))`
- `summary TEXT` (2–3 sentence LLM post-call summary)
- `disconnect_reason VARCHAR(255)`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Table 6: `call_transcripts`
Ordered utterance stream between caller, AI agent, and human supervisor.
- `id BIGSERIAL PRIMARY KEY`
- `session_id UUID NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE`
- `role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'agent', 'supervisor'))`
- `content TEXT NOT NULL`
- `sequence INTEGER NOT NULL`
- `spoken_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- *Constraint:* `UNIQUE (session_id, sequence)` to guarantee order and prevent duplicate turns.

#### Table 7: `latency_logs`
Discrete turn timing telemetry for performance tracking.
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `session_id UUID NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE`
- `step VARCHAR(20) NOT NULL CHECK (step IN ('stt', 'llm', 'tts', 'e2e'))`
- `duration_ms DOUBLE PRECISION NOT NULL CHECK (duration_ms >= 0)`
- `logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Table 8: `handoff_events`
Audit trail of human supervisor live audio takeovers and hand-backs.
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `session_id UUID NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE`
- `supervisor_id UUID REFERENCES supervisors(id) ON DELETE SET NULL`
- `action VARCHAR(50) NOT NULL CHECK (action IN ('takeover', 'return_to_ai', 'disconnect'))`
- `notes TEXT`
- `timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()`

### 11.2 Critical Query Indexes
- `idx_customers_phone` on `customers(phone)`: B-Tree unique for sub-millisecond phone verification during speech.
- `idx_call_sessions_status_started` on `call_sessions(status, started_at DESC)`: Optimizes dashboard active calls polling.
- `idx_transcripts_session_seq` on `call_transcripts(session_id, sequence ASC)`: Optimizes live transcript polling.
- `idx_tickets_status` on `tickets(status, created_at DESC)`: Optimizes supervisor queue view.
- `idx_appointments_date` on `appointments(appointment_date, status)`: Schedule slot view.

---

## 12. Frontend Applications Architecture

### 12.1 Customer Web Client (`frontend/`)
- **Technology:** React 18, `livekit-client`, vanilla CSS design tokens (`design-system.css`).
- **WebRTC Helper (`frontend/src/livekit_client.js`):**
  - Manages LiveKit `Room` instance.
  - Automatically handles browser audio track attachment:
    ```javascript
    room.on(RoomEvent.TrackSubscribed, (track) => {
      if (track.kind === 'audio') {
        const audioElement = track.attach();
        document.body.appendChild(audioElement); // Explicit DOM append prevents browser garbage collection
      }
    });
    ```
  - Enables browser WebRTC audio constraints: `echoCancellation: true`, `noiseSuppression: true`, `autoGainControl: true`.
- **UI Components:**
  - `JoinRoom.jsx`: Pre-call form capturing caller name and support room ID.
  - `CallScreen.jsx`: Active call UI featuring the **Glowing Voice Orb Visualizer**:
    - *Idle / Listening:* Subtle blue/purple breathing animation.
    - *Epixa Speaking:* Vibrant pulsing gradient with scaling outer rings.
    - *Muted:* Muted red/amber outline.
  - Call duration timer, mic mute/unmute button (`MicButton.jsx`), and end call button.

### 12.2 Supervisor Admin Dashboard (`dashboard/`)
- **Technology:** React 18, `livekit-client`, `@supabase/supabase-js`, `lucide-react`.
- **UI Components:**
  - `LoginScreen.jsx`: Supabase Auth supervisor sign-in form.
  - `ActiveCallsList.jsx`: Auto-polls `GET /api/v1/rooms/active-sessions` every 3 seconds, rendering status badges (`active` green, `escalated` red/amber, `completed` grey).
  - `TranscriptView.jsx`: Auto-polls `GET /api/v1/rooms/{session_id}/transcript` every 1.5 seconds, displaying real-time conversation bubbles with timestamps.
  - `JoinCallButton.jsx`: Live audio takeover button, mic controls, and "Hand back to AI" control.

---

## 13. Performance Optimizations & Latency Telemetry

### 13.1 Cold-Start Elimination & Model Pre-Warming
- **Silero VAD Plugin:** Pre-loaded at module startup (`silero.VAD.load()`).
- **ChromaDB SentenceTransformer:** Pre-warmed by executing a dummy query (`query_faq("warmup")`) during agent initialization. This eliminates a **6–9 second cold-start penalty** on the customer's first question.

### 13.2 Streaming Audio Synthesis
- Deepgram Aura streaming synthesis begins emitting audio chunks immediately as tokens stream from Groq LLM, avoiding waiting for the full sentence to generate.

### 13.3 Discrete Turn Telemetry (`LatencyTracker` in `agent/utils.py`)
Tracks individual turn stages:
- `stt`: Speech-to-text processing time (~250–400ms).
- `llm`: Groq Llama 3.1 generation time (~250–350ms).
- `tts`: Time to first synthesized audio buffer (~150–250ms).
- **Total User-Perceived Turnaround Latency: ~800ms – 1.1s.**

### 13.4 Inactivity Timeout Watchdog
In `agent/main.py`:
- Monitors silence in 30-second intervals.
- If customer is silent for `SESSION_TIMEOUT_MINUTES = 1`:
  1. Epixa speaks: *"It seems you may have stepped away. I'll end our session now. Feel free to call back anytime. Goodbye!"*
  2. Cleanly terminates the room with status `"timeout"`.

---

## 14. Critical Engineering Nuances & Hard-Earned Bug Fixes

Any AI or engineer modifying this codebase must be aware of these non-obvious implementation details:

### 1. The `ctx.room.sid` Asynchronous Deadlock Bug
- **Issue**: In LiveKit Python SDK, `ctx.room.sid` is a coroutine property until the server completes room handshake. Awaiting `ctx.room.sid` directly in the synchronous entrypoint blocked agent initialization for 30–40 seconds, causing silent call failure.
- **Fix**: The agent immediately connects without awaiting `room.sid`. A background task (`update_room_sid_background()`) awaits the SID asynchronously and writes it to the DB once ready.

### 2. Multi-Participant WebRTC Track Isolation
- **Issue**: When a human supervisor joins a call, the AI agent would hear the supervisor speaking and attempt to reply to them, causing overlapping audio.
- **Fix**: The AI agent listens to `track_published` and `track_subscribed` events. If the participant identity starts with `agent_` or `human_`, it calls `publication.set_subscribed(False)`, completely cutting the supervisor's audio out of the AI's STT pipeline.

### 3. DOM Garbage Collection of WebRTC Audio Elements
- **Issue**: In Chrome and Safari, `track.attach()` creates an `HTMLAudioElement`. If this element is not appended to the live DOM (`document.body.appendChild(audioElement)`), browser garbage collection destroys the audio node after ~15–30 seconds, causing the user to suddenly hear silence.
- **Fix**: `LiveKitHelper` in `frontend/src/livekit_client.js` explicitly appends audio elements to `document.body` and manages a cleanup map `audioElements`.

### 4. False-Positive Escalation Prevention
- **Issue**: Simple substring matching on `"human"` triggers false escalations when callers say *"superhuman"* or *"I do not want a human"*.
- **Fix**: Replaced simple substring checks with strict word-boundary regex patterns targeting explicit transfer intent phrases.

### 5. Stale Call Auto-Healing Grace Period
- **Issue**: If the supervisor dashboard polled `/api/rooms/active-sessions` while a customer was still in the 3-second token exchange/handshake phase, the backend would see the room missing on LiveKit and prematurely mark the session `completed`.
- **Fix**: Added a 60-second age threshold. Sessions under 60 seconds old are never auto-healed, giving callers time to connect.

---

## 15. Environment Configuration & Operational Run Guide

### 15.1 Environment Variables (`.env`)
```env
# =============================================================================
# LIVEKIT CLOUD (WebRTC RTC Infrastructure)
# =============================================================================
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret

# =============================================================================
# GROQ CLOUD (High-Speed LLM Inference)
# =============================================================================
GROQ_API_KEY=gsk_your_groq_api_key

# =============================================================================
# DEEPGRAM (Speech-to-Text & Text-to-Speech)
# =============================================================================
DEEPGRAM_API_KEY=your-deepgram-api-key
DEEPGRAM_STT_API_KEY=your-deepgram-api-key
DEEPGRAM_TTS_API_KEY=your-deepgram-api-key

# =============================================================================
# FASTAPI BACKEND CONFIGURATION
# =============================================================================
PORT=8000
BACKEND_URL=http://127.0.0.1:8000
SUPERVISOR_SECRET_KEY=your-supervisor-secret-key-for-admin-minting

# =============================================================================
# DEDICATED SUPABASE POSTGRESQL & AUTH
# =============================================================================
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### 15.2 Operational Run Instructions

#### Option 1: Multi-Process Runner (`start.sh`)
```bash
chmod +x start.sh
./start.sh
```
- Spawns all 4 processes inside a `tmux` session named `voice-ai`.
- Attach: `tmux attach-session -t voice-ai`
- Switch tabs: `Ctrl+b` then `0` (Backend), `1` (Agent), `2` (Frontend), `3` (Dashboard)
- Terminate: `tmux kill-session -t voice-ai`

#### Option 2: 4 Separate Terminals
1. **Terminal 1 — FastAPI Backend**:
   ```bash
   source backend/venv/bin/activate
   python backend/main.py
   # Runs on http://localhost:8000
   ```
2. **Terminal 2 — LiveKit Voice Agent Worker**:
   ```bash
   source agent/venv/bin/activate
   cd agent
   python main.py dev
   # Connects to LiveKit Cloud worker queue
   ```
3. **Terminal 3 — Customer Web Application**:
   ```bash
   cd frontend
   npm start
   # Runs on http://localhost:3000
   ```
4. **Terminal 4 — Admin Supervisor Dashboard**:
   ```bash
   cd dashboard
   npm start
   # Runs on http://localhost:3001
   ```

---

## 16. Technical Debt Register & Refactoring Status

| Priority | Issue / Debt | Root Cause | Production Solution | Status |
| :--- | :--- | :--- | :--- | :--- |
| **P0** | **Unauthenticated Token Escalation** | `POST /api/token` accepted `role: "agent"` freely | Replaced with `POST /api/v1/calls` (audio-only) and authenticated `/takeover` | **Resolved** |
| **P0** | **Missing `.gitignore`** | Accidental omission in prototype | Created strict root `.gitignore` protecting secrets, DBs, and logs | **Resolved** |
| **P0** | **Zero Automated Tests** | Prototype code | Comprehensive `pytest` test suites across core, api, and agent | **Resolved** |
| **P1** | **Architectural Coupling** | `sys.path.insert` in `agent/main.py` | Standalone `epoxa_core` package consumed via `uv` workspace | **Resolved** |
| **P1** | **Asymmetric Dual-Write** | SQLite has customers/tickets, Supabase has latencies | Unified dedicated Supabase PostgreSQL schema with 12 tables & Alembic | **Resolved** |
| **P1** | **Unbounded Queries** | `SELECT * FROM call_sessions` polled every 3s | Bounded queries with pagination, indexes, and real-time SSE | **Resolved** |
| **P2** | **GET Request Side-Effects** | `GET /active-sessions` mutated stale room status | Dedicated advisory-locked background reconciliation worker | **Resolved** |
| **P2** | **Simulated Appointments** | `agent/nodes.py` produced codes without DB write | `appointments` table with `AppointmentService` slot validation & DB write | **Resolved** |
