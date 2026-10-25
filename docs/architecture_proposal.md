# Phase B: Target Architecture & Engineering Proposal
**Project Name:** Epoxa — Voice AI Agent  
**Author:** Principal Software Architecture & Engineering  
**Status:** Proposal / Specification  

---

## 1. Architectural Vision & Principles

The goal of this architectural refactoring is to evolve **Epoxa — Voice AI Agent** into a reliable, maintainable, secure, and testable system while preserving:
- Current customer experience (conversational persona "Epixa", company "Epoxcel", glowing voice orb UI).
- Supervisor command center workflows (active calls monitoring, live transcripts, live audio takeover, hand-back).
- Real-time streaming voice latency under ~1.0s.

### Core Principles
1. **Separation of Concerns**: Business domain rules must not live in HTTP controllers or LiveKit event handlers.
2. **Explicit Dependency Flow**: The agent worker and backend API should share common domain contracts and repositories, eliminating cross-directory `sys.path` hacks.
3. **Defense-in-Depth Security**: Public endpoints must never mint privileged supervisor credentials without authorization. Input schemas must be strictly bounded.
4. **Authoritative Persistence & Recoverability**: Clearly define single sources of truth, indexed queries, and reliable data synchronization.
5. **Continuous Verifiability**: Every architectural layer must be covered by automated unit and integration tests with deterministic mock fixtures for external AI services.

---

## 2. Target Layered Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             PRESENTATION CLIENTS                                 │
│  - Customer Web App (React @ :3000)      - Supervisor Dashboard (React @ :3001)  │
└───────────────────────────────┬──────────────────────────┬───────────────────────┘
                                │ WebRTC / HTTP            │ WebRTC / HTTP
                                ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (`epoxa_api`)                                  │
│  - FastAPI Routes (Versioned: `/api/v1/`)                                        │
│  - Request Validation & Response Serialization (Pydantic v2)                     │
│  - Authentication & Authorization Dependencies (Supervisor Token Guard)          │
│  - Global Exception Handling & Correlation ID Middleware                         │
└───────────────────────────────────────┬──────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      APPLICATION / SERVICE LAYER                                 │
│  - Token Service (Role-based JWT generation & validation)                        │
│  - Customer Service (Identity verification & onboarding orchestration)           │
│  - Ticket Service (Complaint logging & escalation dispatch)                      │
│  - Room & Session Service (Session lifecycle, stale call reconciliation)         │
└───────────────────────┬──────────────────────────────────┬───────────────────────┘
                        │                                  │
                        ▼                                  ▼
┌──────────────────────────────────────┐  ┌────────────────────────────────────────┐
│            DOMAIN LAYER              │  │          VOICE AGENT LAYER             │
│  - Customer, Ticket, Session Entities│  │  (`epoxa_agent`)                       │
│  - Business Rules & Invariants       │  │  - LiveKit Pipeline Orchestrator       │
│  - Domain Value Objects & Enums      │  │  - LangGraph State Machine             │
│  - Domain Exception Hierarchy        │  │  - Handoff & Takeover Manager          │
└───────────────────────┬──────────────┘  └──────────────────┬─────────────────────┘
                        │                                    │
                        ▼                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                       INFRASTRUCTURE & PROVIDER LAYER                            │
│  - Database Repositories (SQLite primary engine with indexed tables)             │
│  - Supabase Cloud Synchronizer (Background queue / recoverable sync)             │
│  - External Provider Adapters:                                                   │
│    • LiveKit RTC Client                                                          │
│    • Deepgram STT / TTS Adapters                                                 │
│    • Groq LLM Adapter (LangChain/OpenAI protocol)                                │
│    • ChromaDB RAG FAQ Adapter                                                    │
│  - Observability, Telemetry & Structured Logging                                 │
│  - Core Typed Settings (`pydantic-settings`)                                     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Boundaries & Repository Layout

To maintain local development simplicity and prevent package version conflicts between LiveKit/PyTorch/Transformers and FastAPI, we retain a coordinated modular repository with a shared core domain package:

```
epoxa/
├── .gitignore                           # Excludes .env, *.db, logs/, caches, node_modules
├── .env.example                         # Safe configuration template
├── README.md                            # Complete engineering documentation
├── Makefile                             # Unified dev commands: test, lint, format, check
├── start.sh                             # Enhanced multi-process runner with health check
│
├── core/                                # SHARED DOMAIN & INFRASTRUCTURE LIBRARY
│   ├── __init__.py
│   ├── config.py                        # Pydantic Settings (Environment variables)
│   ├── logging.py                       # Unified structured logger (console + rotating file)
│   ├── models/                          # Domain models & TypedDicts (Customer, Ticket, Session, Latency)
│   ├── exceptions.py                    # Domain exceptions (VerificationError, TokenError, etc.)
│   └── database/                        # Persistence Layer
│       ├── connection.py                # SQLite thread-safe connection factory
│       ├── schema.py                    # DDL migrations & index creation
│       ├── repositories/                # Clean repository pattern:
│       │   ├── customer_repo.py
│       │   ├── ticket_repo.py
│       │   ├── session_repo.py
│       │   └── transcript_repo.py
│       └── supabase_sync.py             # Cloud mirror synchronizer with error handling
│
├── backend/                             # FASTAPI REST API SERVICE
│   ├── main.py                          # Lifespan manager, CORS, router mounting
│   ├── dependencies.py                  # Auth guards, DB repository injection
│   ├── routes/
│   │   ├── auth.py                      # Token generation with supervisor key guard
│   │   ├── rooms.py                     # Room listing, creation, and session queries
│   │   ├── customers.py                 # Customer listing, verify, register
│   │   ├── tickets.py                   # Ticket creation & listing
│   │   └── health.py                    # Liveness & readiness probes
│   └── schemas/                         # Pydantic request/response schemas with bounds
│
├── agent/                               # LIVEKIT REAL-TIME VOICE WORKER
│   ├── main.py                          # Worker lifecycle, Silero VAD, Deepgram STT/TTS pipeline
│   ├── graph_builder.py                 # LangGraph StateGraph, custom LangGraphLLM adapter
│   ├── nodes/                           # Clean modular dialogue nodes
│   │   ├── router.py                    # Intent classification & flow preservation
│   │   ├── greeting.py
│   │   ├── verify.py
│   │   ├── registration.py
│   │   ├── appointment.py
│   │   ├── complaint.py
│   │   ├── faq.py
│   │   ├── escalate.py
│   │   └── chat.py
│   ├── handoff.py                       # Handoff state tracker & supervisor audio filtering
│   ├── chroma_client.py                 # ChromaDB client & vector search
│   └── embed_documents.py               # Ingestion script for FAQ files
│
├── frontend/                            # CUSTOMER REACT APP (Port 3000)
│   └── src/
│       ├── livekit_client.js            # LiveKitHelper WebRTC audio lifecycle
│       └── components/                  # Voice orb, call screen, connection indicator
│
├── dashboard/                           # SUPERVISOR ADMIN DASHBOARD (Port 3001)
│   └── src/
│       └── components/                  # Active calls list, transcript stream, takeover controls
│
├── tests/                               # AUTOMATED TEST SUITE
│   ├── conftest.py                      # Test fixtures, mock databases, mock providers
│   ├── unit/                            # Unit tests for domain, nodes, routing, repositories
│   ├── integration/                     # FastAPI endpoint tests using TestClient
│   └── agent/                           # Mock voice pipeline & state graph tests
│
└── docs/                                # DOCUMENTATION & ADRs
    ├── audit_report.md
    └── architecture_proposal.md
```

---

## 4. Database & Persistence Strategy

### 4.1 Persistence Responsibilities
1. **SQLite (`backend/voice_support.db`)**: Primary authoritative local datastore.
   - Handles all transactional workloads: customers, tickets, call sessions, transcripts.
   - Enforces Foreign Key constraints (`PRAGMA foreign_keys = ON`).
   - Indexes added to critical query columns:
     - `CREATE INDEX idx_customers_phone ON customers(phone);`
     - `CREATE INDEX idx_tickets_customer ON tickets(customer_id);`
     - `CREATE INDEX idx_sessions_room ON call_sessions(room_name);`
     - `CREATE INDEX idx_transcripts_session ON call_transcripts(session_id, sequence);`
2. **Supabase PostgreSQL**: Remote persistent mirror for analytics and dashboard reporting.
   - All cloud sync operations execute through a non-blocking queue or background executor.
   - If cloud sync fails, failures are captured in a local `sync_queue` table or logged with structured error tags, ensuring zero disruption to live audio streaming.
3. **Appointment Persistence**:
   - An `appointments` table will be added to SQLite:
     ```sql
     CREATE TABLE IF NOT EXISTS appointments (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         customer_id INTEGER,
         date TEXT NOT NULL,
         time TEXT NOT NULL,
         confirmation_code TEXT UNIQUE NOT NULL,
         status TEXT DEFAULT 'confirmed',
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         FOREIGN KEY (customer_id) REFERENCES customers(id)
     );
     ```

---

## 5. Security & Authentication Model

1. **Role-Based Token Generation**:
   - `POST /api/token` default role is `customer`.
   - Requesting `role: "agent"` requires a valid `X-Supervisor-Key` header matching `SUPERVISOR_SECRET_KEY` from configuration.
   - Public requests with `role: "agent"` and no valid key receive `403 Forbidden`.
2. **Strict Request Validation**:
   - Input payloads validate length, strip whitespace, and reject malformed inputs.
   - Ticket descriptions capped at 2,000 characters.
   - Customer phone validated strictly (10–15 digits).
3. **Health & Diagnostics Security**:
   - `/health/live`: Unauthenticated simple 200 OK ping.
   - `/health/ready`: Checks internal component connectivity without exposing customer metrics or credential secrets.

---

## 6. Voice Agent Lifecycle & Handoff State Machine

```
[Start Session]
      │
      ▼
[Greeting Node] ────► [Active AI Conversation]
                              │
               ┌──────────────┴──────────────┐
               │                             │
    (Customer says "human"         (Supervisor clicks
     or 3 failed verifications)     "Join Live Call")
               │                             │
               ▼                             ▼
       [Escalated State]             [Audio Takeover]
       (AI worker muted)             (Supervisor connects)
               │                             │
               └──────────────┬──────────────┘
                              │
                    [Human Agent Speaks]
               (AI unsubs from agent_* track)
                              │
                    [Supervisor clicks
                    "Hand back to AI"]
                              │
                              ▼
                   LiveKit Data Packet:
                  { "action": "resume" }
                              │
                              ▼
                   [Resume Greeting Spoken]
                              │
                              ▼
                 [AI Conversation Resumed]
```

---

## 7. Phased Implementation Sequence

1. **Phase C (Foundations & Security Baseline)**:
   - Create root `.gitignore` to protect credentials and data.
   - Establish `core/` package with typed `Settings` (`pydantic-settings`) and structured logging.
   - Set up `pytest` framework, configuration, and base fixtures.
2. **Phase D (Backend & Persistence Refactoring)**:
   - Refactor database layer into clean repositories with SQLite indexing and thread safety.
   - Implement role protection on `POST /api/token` (`X-Supervisor-Key`).
   - Add input validation, pagination on active sessions, and split health probes.
   - Write unit and integration test suite for backend routes and repositories.
3. **Phase E (Voice Agent & State Machine Refactoring)**:
   - Clean up imports, eliminating `sys.path.insert` by leveraging `core/`.
   - Modularize `agent/nodes.py` into distinct single-responsibility modules.
   - Add persistence for appointment booking.
   - Write mock tests for LangGraph state machine routing, phone extraction, and handoff.
4. **Phase F (Frontend Stabilization & Tooling)**:
   - Add frontend unit tests for LiveKit connection helper and call screens.
   - Create Makefile with `test`, `lint`, and `check` targets.
5. **Phase G (Verification & Handover)**:
   - Execute all test suites, builds, and linters.
   - Produce Final Engineering Report.
