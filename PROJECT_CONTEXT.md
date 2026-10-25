# Epoxa — Full Project Context & Technical Reference

> **Purpose**: This single, self-contained document serves as the master technical blueprint and context document for Epoxa. It is designed to be provided to any AI coding assistant or engineer to instantly understand the business requirements, system architecture, database schema, API contracts, security boundaries, and development workflows without requiring external access.

---

## 1. Executive Summary & Core Mission

**Epoxa** is a production-grade, web-based AI voice customer support platform designed for modern enterprises.

### Core Value Proposition
- **Zero Friction Customer Experience**: Customers engage in low-latency, natural spoken voice conversations directly from their web browser. No customer accounts, logins, passwords, or PSTN/telephony (Twilio/carrier) phone infrastructure are required.
- **Strictly Grounded Knowledge**: The AI support assistant answers questions strictly using verified organizational knowledge chunks (FAQs, return policies, warranty rules). If an answer is not present, it triggers a safe fallback: *"I don't have that information in our official guidelines. Would you like me to connect you with a supervisor or open a support ticket?"*
- **Live Supervisor Oversight & Seamless Takeover**: Human supervisors authenticate via a dedicated dashboard where they observe active calls in real time with live streaming transcripts, sentiment flags, and ticket queues. Supervisors can take over an active call instantly (muting the AI agent's audio track) and hand back control to the AI with clean state transition.
- **Enterprise Multi-Tenancy**: Built from the ground up with tenant isolation (`organizations` -> `businesses` -> `business_locations`), composite foreign keys, and server-side authorization enforcement.
- **Data Privacy & 30-Day Retention**: Strict data minimization compliant with GDPR/CCPA. Voice conversation transcripts are permanently redacted/purged after 30 days via an automated retention job, while preserving audit metrics, call duration, and ticket records.

---

## 2. Complete Technology Stack

### Backend
- **Runtime & Language**: Python 3.11+ / 3.14 compatible.
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com) 0.115+ (async request handling, correlation ID middleware, Pydantic validation, OpenAPI documentation).
- **ORM & Data Access**: SQLAlchemy 2.0 (fully asynchronous engine via `async_sessionmaker`, declarative models with cross-platform GUID types and UTC timestamps).
- **Database**: PostgreSQL 17 (hosted on Supabase, connected via `postgresql+asyncpg://`).
- **Database Migrations**: [Alembic](https://alembic.sqlalchemy.org) 1.13+ (revision-controlled migration scripts).
- **Configuration & Validation**: [Pydantic v2](https://docs.pydantic.dev/) and `pydantic-settings` with secret redaction in logs.
- **LLM & Agent Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) / LangChain orchestration with bounded tool calling and state management.
- **Inference Provider**: [Groq](https://groq.com) (`llama-3.3-70b-versatile`) for ultra-low-latency completions, with OpenAI (`gpt-4o-mini`) as a configured fallback.
- **Speech Services**: [Deepgram](https://deepgram.com) Nova-2 for Speech-to-Text (STT) and Deepgram Aura (`aura-asteria-en`) for Text-to-Speech (TTS).
- **Real-Time WebRTC Media Transport**: [LiveKit Cloud](https://livekit.io) (room-scoped token generation, WebRTC audio streaming, participant tracks).
- **Authentication**: [Supabase Auth](https://supabase.com/docs/guides/auth) with server-side JWKS cryptographic signature verification, audience validation, and tenant membership resolution.
- **Test Suite**: `pytest` and `pytest-asyncio` with 11 automated unit and integration tests.

### Frontend
- **Framework**: [React 18.3+](https://react.dev) with [TypeScript 5.6+](https://www.typescriptlang.org).
- **Build System & Dev Server**: [Vite](https://vitejs.dev) with fast HMR.
- **Design System & Styling**: Curated Vanilla CSS using an HSL dark color palette, glassmorphism, responsive flex/grid layouts, and zero heavy UI framework overhead (Tailwind-free).
- **Audio & Media Visualizer**: Custom HTML5 Canvas audio wave visualizer powered by Web Audio API (`AudioContext`, `AnalyserNode`) and LiveKit Client SDK.
- **Icons**: Lucide React icons.

### Tooling & Automation
- **Package Management**: `uv` and `pip` for Python; `npm` for Node.js.
- **Workflow Orchestration**: `Makefile` providing standardized commands for installation, linting, testing, migrations, database seeding, retention cleanup, and development servers.

---

## 3. Directory Layout & File Map

```text
epoxa/
├── backend/
│   ├── alembic/                         # Database schema migrations
│   │   ├── env.py                       # Async Alembic migration runner
│   │   ├── script.py.mako               # Migration template
│   │   └── versions/
│   │       └── 001_initial_schema.py    # Complete DDL for 15+ normalized tables
│   ├── alembic.ini                      # Alembic configuration
│   ├── pytest.ini                       # Pytest test discovery settings
│   ├── app/
│   │   ├── main.py                      # FastAPI app factory, CORS, correlation ID, exception handlers
│   │   ├── api/
│   │   │   └── v1/                      # Versioned REST API routes
│   │   │       ├── router.py            # Master v1 router aggregation
│   │   │       ├── health.py            # /health/live & /health/ready diagnostic probes
│   │   │       ├── auth.py              # /api/v1/auth/me & dev-token generator
│   │   │       ├── voice.py             # /api/v1/voice/token, turn, end endpoints
│   │   │       ├── calls.py             # /api/v1/calls/active, transcripts, takeover, handback
│   │   │       ├── tickets.py           # /api/v1/tickets CRUD & status transition endpoints
│   │   │       ├── customers.py         # /api/v1/customers profile & phone lookup
│   │   │       └── knowledge.py         # /api/v1/knowledge/search FAQ retrieval
│   │   ├── core/
│   │   │   ├── config.py                # Typed Pydantic BaseSettings, secret redaction
│   │   │   ├── exceptions.py            # Hierarchical domain exceptions (TenantMismatch, etc.)
│   │   │   ├── logging.py               # Structured JSON logger with correlation IDs
│   │   │   └── security.py              # Auth token extractor & dependency injection
│   │   ├── db/
│   │   │   ├── base.py                  # DeclarativeBase with GUID & UTC DateTime types
│   │   │   └── session.py               # Async engine & get_db async session generator
│   │   ├── models/                      # SQLAlchemy 2.0 ORM domain entities
│   │   │   ├── base.py                  # GUID type & timestamp mixins
│   │   │   ├── tenant.py                # Organization, Business, BusinessLocation, SupervisorProfile, Membership
│   │   │   ├── customer.py              # Customer profile records
│   │   │   ├── voice.py                 # CallSession, CallEvent, Transcript, CallSummary
│   │   │   ├── ticket.py                # SupportTicket, Escalation, TakeoverEvent
│   │   │   └── knowledge.py             # KnowledgeDocument, KnowledgeChunk, AgentConfig
│   │   ├── schemas/                     # Pydantic v2 validation models
│   │   │   ├── common.py                # Pagination & base response envelopes
│   │   │   ├── auth.py                  # Token & Supervisor profile schemas
│   │   │   ├── tenant.py                # Organization & Business schemas
│   │   │   ├── customer.py              # Customer create, update, lookup schemas
│   │   │   ├── voice.py                 # Token request, turn input, call summary schemas
│   │   │   ├── ticket.py                # Ticket create, patch, filter schemas
│   │   │   └── knowledge.py             # Knowledge chunk & search schemas
│   │   ├── repositories/                # Tenant-scoped data access repositories
│   │   │   ├── tenant_repo.py           # Org & membership queries
│   │   │   ├── customer_repo.py         # Customer lookup & deduplication
│   │   │   ├── voice_repo.py            # Call session, transcript turns, events, summaries
│   │   │   ├── ticket_repo.py           # Ticket CRUD, status updates, escalation logs
│   │   │   └── knowledge_repo.py        # Knowledge chunk retrieval & agent configs
│   │   ├── services/                    # Business use-cases & domain logic
│   │   │   ├── auth_service.py          # Supervisor verification & tenant context resolution
│   │   │   ├── voice_service.py         # LiveKit token issuance & call state management
│   │   │   ├── handoff_service.py       # Supervisor takeover & handback state machine
│   │   │   ├── customer_service.py      # Customer profile resolution
│   │   │   ├── ticket_service.py        # Ticket creation, assignment, number sequencing
│   │   │   └── retention_service.py     # 30-day transcript redaction executor
│   │   ├── agents/                      # AI orchestration & tool definitions
│   │   │   ├── orchestrator.py          # Conversation turn orchestrator
│   │   │   ├── tools.py                 # search_knowledge_base, create_support_ticket, update_customer_details, request_supervisor_escalation
│   │   │   └── prompts.py               # Grounded system prompts & summary prompts
│   │   ├── integrations/                # Third-party SDK isolation adapters
│   │   │   ├── livekit.py               # LiveKit AccessToken generator
│   │   │   ├── speech.py                # Deepgram STT/TTS adapter
│   │   │   ├── llm.py                   # Groq / OpenAI LLM caller
│   │   │   └── supabase_auth.py         # JWKS signature verifier & public key caching
│   │   └── scripts/
│   │       ├── seed_demo.py             # Deterministic synthetic demo tenant seed
│   │       ├── cleanup_retention.py     # 30-day transcript redaction runner
│   │       └── verify_db_target.py      # Non-destructive database target verifier
│   └── tests/
│       ├── conftest.py                  # Async DB fixtures & mock tokens
│       ├── test_tenant_isolation.py     # Verifies zero cross-tenant data leakage
│       ├── test_handoff_state_machine.py# Validates takeover & handback transitions
│       ├── test_api_endpoints.py        # Health, voice token, tickets, calls
│       ├── test_seed_demo.py            # Validates seed script idempotency
│       └── test_retention.py            # Validates 30-day transcript purge
├── frontend/
│   ├── index.html                       # Single-page application entry point
│   ├── package.json                     # React, TypeScript, Vite dependencies
│   ├── tsconfig.json                    # Strict TypeScript configuration
│   ├── vite.config.ts                   # Vite configuration with proxy to backend :8000
│   └── src/
│       ├── main.tsx                     # React root mount
│       ├── App.tsx                      # Root navigation, view toggling, authentication state
│       ├── index.css                    # Design system (HSL tokens, typography, dark mode)
│       ├── api/                         # Strongly typed API client (`fetchClient`)
│       ├── types/                       # Shared TypeScript models (CallSession, Ticket, etc.)
│       ├── components/
│       │   ├── Navbar.tsx               # Top navigation & role switcher
│       │   ├── VoiceVisualizer.tsx      # Canvas real-time audio wave animation
│       │   ├── Badge.tsx                # Status and priority badges
│       │   └── Modal.tsx                # Accessible modal dialog
│       └── views/
│           ├── CustomerVoiceView.tsx    # Customer voice call interface (mic controls, audio visualizer, turn transcript)
│           └── supervisor/
│               ├── SupervisorLogin.tsx     # Demo & Supabase supervisor authentication
│               ├── SupervisorDashboard.tsx # Real-time supervisor operations center
│               ├── ActiveCallsList.tsx     # Active/escalated calls with live indicators
│               ├── TakeoverPanel.tsx       # Interactive takeover/handback audio controls
│               ├── CallHistoryView.tsx     # Historical calls, AI summary, transcript modal
│               └── TicketBoardView.tsx     # Support ticket Kanban / table with status filtering
├── docs/                                # Technical specifications
│   ├── PRD.md                           # Product Requirements Document
│   ├── architecture.md                  # System architecture & trust boundaries
│   ├── database-erd.md                  # Entity Relationship Diagram & Mermaid specification
│   ├── data-dictionary.md               # Complete schema definitions, data types, constraints
│   ├── tenant-isolation.md              # Multi-tenant matrix & threat model
│   ├── architecture-decisions.md        # Architectural Decision Records (ADRs 001-005)
│   ├── API.md                           # Complete REST API documentation
│   ├── setup-and-migrations.md          # Database setup and migration guides
│   ├── security-and-privacy.md          # Security policy, credential handling, retention
│   └── implementation-status.md         # Milestone progress tracker
├── .env.example                         # Safe configuration template with redacted secrets
├── Makefile                             # Automation commands
├── pyproject.toml                       # Python package dependencies & tools
└── README.md                            # Project overview & quickstart
```

---

## 4. Key Subsystems & Architecture Deep Dive

### 4.1. Real-Time Voice Audio Pipeline
```mermaid
sequenceDiagram
    autonumber
    actor Customer as Browser Customer
    participant API as FastAPI Backend
    participant LiveKit as LiveKit WebRTC SFU
    participant Agent as LangGraph Orchestrator
    participant Deepgram as Deepgram (STT / TTS)
    participant Groq as Groq (Llama-3.3-70B)
    actor Supervisor as Supervisor Dashboard

    Customer->>API: POST /api/v1/voice/token {customer_name, customer_phone}
    API->>API: Lookup/create Customer record & CallSession (status='initiating')
    API->>LiveKit: Generate room token (room_name="epoxa-room-...")
    API-->>Customer: Return {token, room_name, session_id, livekit_url}
    Customer->>LiveKit: Connect WebRTC Audio Track
    Customer->>Deepgram: Stream customer microphone audio (Nova-2 STT)
    Deepgram-->>Customer: Transcribed text turn
    Customer->>API: POST /api/v1/voice/sessions/{id}/turn {speech: "..."}
    API->>Agent: handle_turn(speech, session_id, org_id)
    Agent->>API: Persist customer transcript turn & event
    Agent->>Groq: Generate completion with tools (search_knowledge_base, etc.)
    alt Tool Call: search_knowledge_base
        Groq-->>Agent: invoke search_knowledge_base("return policy")
        Agent->>API: Query knowledge_chunks for organization_id
        API-->>Agent: Matching FAQ passages
        Agent->>Groq: Formulate grounded conversational reply
    end
    Groq-->>Agent: Grounded response text
    Agent->>API: Persist AI transcript turn & event
    Agent->>Deepgram: Synthesize voice audio (Aura TTS)
    Agent-->>Customer: Return reply text & audio stream
    Customer->>Customer: Render Canvas wave animation & play audio
```

### 4.2. Human Supervisor Takeover & Handback State Machine
- **Call Session Statuses**: `initiating` ➔ `active` ➔ `escalated` ➔ `supervisor_takeover` ➔ `completed` | `failed`.
- **Handoff States**: `none` ➔ `requested` ➔ `accepted` ➔ `rejected` ➔ `returned_to_ai`.

#### The Takeover Workflow:
1. **Escalation**: Triggered either automatically when the LLM orchestrator calls `request_supervisor_escalation` (e.g., caller frustrated or out of policy), or explicitly by customer voice request. The call session transitions to `status = 'escalated'`, `handoff_state = 'requested'`.
2. **Supervisor Alert**: Active calls polling on the supervisor dashboard highlights the call with a pulsing red badge and displays live transcripts.
3. **Takeover Execution**: The supervisor clicks **"Take Over Call"**.
   - Frontend calls `POST /api/v1/calls/{session_id}/takeover`.
   - FastAPI verifies supervisor's organizational membership.
   - `handoff_service` logs a `takeover_events` record (`action = 'takeover_started'`).
   - Session transitions to `status = 'supervisor_takeover'`, `handoff_state = 'accepted'`.
   - The AI agent's audio output is suppressed/muted.
   - A supervisor LiveKit room token is issued, allowing the supervisor to speak directly to the customer over WebRTC.
4. **Handback to AI**: Once the supervisor resolves the critical point:
   - Supervisor clicks **"Hand back to AI"**.
   - Frontend calls `POST /api/v1/calls/{session_id}/handback` with optional resolution notes.
   - `handoff_service` logs `takeover_events` (`action = 'handback_to_ai'`).
   - Session transitions back to `status = 'active'`, `handoff_state = 'returned_to_ai'`.
   - AI agent audio is unmuted. A synthetic context injection informs the agent of the supervisor's resolution notes so the agent can naturally conclude the call.
5. **Call Conclusion & Summary**: When the call concludes:
   - `POST /api/v1/voice/sessions/{session_id}/end` computes duration and marks session `status = 'completed'`.
   - Automated AI summarization generates an objective summary, detects sentiment (`positive`, `neutral`, `negative`, `frustrated`), primary intent, and `follow_up_required` flag, storing it in `call_summaries`.

### 4.3. Grounded Knowledge Retrieval & Safety Boundaries
- **No Hallucination Policy**: The agent is strictly constrained by its system prompt (`prompts.py`) to answer only using content returned by `search_knowledge_base`.
- **Safe Fallback**: If retrieved passages do not answer the question or confidence is low, the agent states:
  > *"I don't have that information in our official guidelines. Would you like me to connect you with a supervisor or open a support ticket?"*
- **Available Agent Tools**:
  1. `search_knowledge_base(query)`: Scans approved `knowledge_chunks` for the active `organization_id`.
  2. `create_support_ticket(title, description, priority, category)`: Creates an official ticket linked to this call and customer.
  3. `update_customer_details(display_name, phone_number, email)`: Links or updates customer details.
  4. `request_supervisor_escalation(reason)`: Flags the call for live supervisor takeover.

### 4.4. Tenant Isolation Matrix & Defense-in-Depth
Epoxa implements strict multi-tenancy across all tiers:
1. **Server-Side Token Verification**: Supervisor identity (`auth.users.id`) is validated using cryptographic signatures against Supabase JWKS. The user's tenant (`organization_id`) is resolved from verified database memberships. Client-supplied tenant IDs in request bodies are never trusted.
2. **Mandatory Tenant Scoping in Repositories**: Every SQL query across `voice_repo`, `ticket_repo`, `customer_repo`, and `knowledge_repo` explicitly filters by `organization_id`. No generic `SELECT * FROM table WHERE id = :id` is permitted.
3. **Composite Foreign Keys & Schema Constraints**: Tables reference `organization_id` directly to prevent cross-tenant referencing at the relational level (e.g., a ticket belonging to Tenant A cannot reference a customer belonging to Tenant B).
4. **Threat Mitigations Tested**:
   - **IDOR Protection**: Accessing an existing resource belonging to another tenant returns `404 Not Found`.
   - **Cross-Tenant Customer Matching**: Phone and email lookups are strictly bound by `WHERE organization_id = :org_id`.
   - **LiveKit Room Hijacking**: Supervisors cannot obtain tokens for rooms outside their authorized organization.

### 4.5. 30-Day Transcript Data Retention Policy
- Compliant with privacy regulations (GDPR/CCPA) and data minimization principles.
- **Mechanism**: `backend/app/scripts/cleanup_retention.py` invokes `retention_service.purge_expired_transcripts(db, retention_days=30)`.
- **Action**: Sets `content = NULL`, `is_purged = TRUE`, and `purged_at = NOW()` for all rows in `transcripts` where `created_at < NOW() - INTERVAL '30 days'`.
- **Preserved Metadata**: Non-sensitive operational audit records (`call_sessions` duration, timestamps, status, `call_summaries`, and `support_tickets`) remain intact for operational reporting and SLA metrics.

---

## 5. Relational Database Schema & Entities

All primary keys use UUIDs (`uuid_generate_v4()`). Timestamps use timezone-aware `TIMESTAMPTZ` set to UTC.

```text
+---------------------------------------------------------------------------------------------------+
|                                        ORGANIZATIONS (Tenant Root)                                |
| id (PK), name, slug (UK), status, created_at, updated_at                                          |
+---------------------------------------------------------------------------------------------------+
       | 1:N                                     | 1:N                            | 1:N
       v                                         v                                v
+----------------------+              +----------------------+         +----------------------+
|      BUSINESSES      |              |  SUPERVISOR_PROFILES |         |      CUSTOMERS       |
| id (PK), org_id (FK),|              | id (PK = Supabase UID|         | id (PK), org_id (FK),|
| name, category, stat |              | email, full_name, st |         | name, phone, email   |
+----------------------+              +----------------------+         +----------------------+
       | 1:N                                     |                                |
       v                                         v (1:N memberships)              |
+----------------------+              +---------------------------+               |
|  BUSINESS_LOCATIONS  |              |  ORGANIZATION_MEMBERSHIPS |               |
| id (PK), business_id |              | id (PK), org_id, sup_id   |               |
| name, address, tz    |              +---------------------------+               |
+----------------------+                                                          |
       |                                                                          |
       +------------------------------------+-------------------------------------+
                                            v
                         +-------------------------------------+
                         |            CALL_SESSIONS            |
                         | id (PK), org_id (FK), customer_id   |
                         | room_name (UK), status, handoff_st  |
                         | started_at, ended_at, duration_sec  |
                         +-------------------------------------+
                            | 1:N         | 1:1          | 1:N
                            v             v              v
                  +-------------+  +--------------+  +-----------------+
                  | TRANSCRIPTS |  | CALL_SUMMARY |  | SUPPORT_TICKETS |
                  | id, call_id,|  | id, call_id, |  | id, org_id,     |
                  | org_id,     |  | org_id,      |  | ticket_num (UK),|
                  | speaker,    |  | summary,     |  | title, priority,|
                  | content,    |  | intent,      |  | category, stat  |
                  | is_purged   |  | sentiment    |  +-----------------+
                  +-------------+  +--------------+           |
                            |                                 v
                            | 1:N                    +-----------------+
                            v                        |   ESCALATIONS   |
                  +-------------+                    | id, org_id,     |
                  | CALL_EVENTS |                    | call_id, reason,|
                  | id, call_id,|                    | state           |
                  | event_type, |                    +-----------------+
                  | payload     |
                  +-------------+
```

### Table Definitions Summary
1. `organizations`: Tenant root (`id`, `name`, `slug`, `status`, timestamps).
2. `businesses`: Business division / brand (`id`, `organization_id`, `name`, `category`, `status`, timestamps).
3. `business_locations`: Physical/virtual branch (`id`, `business_id`, `name`, `address`, `timezone`, timestamps).
4. `supervisor_profiles`: Staff accounts (`id` matching Supabase Auth UID, `email`, `full_name`, `status`, timestamps).
5. `organization_memberships`: Links supervisors to tenants (`id`, `organization_id`, `supervisor_id`, `role` in `admin|supervisor`).
6. `customers`: End-user caller records (`id`, `organization_id`, `business_id`, `display_name`, `phone_number`, `email`, `company_name`, `metadata`).
7. `call_sessions`: Voice call sessions (`id`, `organization_id`, `customer_id`, `room_name`, `status`, `handoff_state`, `started_at`, `ended_at`, `duration_seconds`, `termination_reason`, `metadata`).
8. `call_events`: Granular call telemetry events (`id`, `call_session_id`, `event_type`, `actor`, `payload`, `created_at`).
9. `transcripts`: Speech dialogue turns (`id`, `call_session_id`, `organization_id`, `speaker`, `content`, `is_purged`, `purged_at`, `created_at`).
10. `call_summaries`: AI-generated session outcomes (`id`, `call_session_id`, `organization_id`, `summary`, `primary_intent`, `detected_sentiment`, `follow_up_required`).
11. `support_tickets`: Tracked customer issues (`id`, `organization_id`, `customer_id`, `call_session_id`, `assigned_supervisor_id`, `ticket_number`, `title`, `description`, `category`, `priority`, `status`, `resolved_at`).
12. `escalations`: Real-time human assistance requests (`id`, `organization_id`, `call_session_id`, `support_ticket_id`, `reason`, `state`, timestamps).
13. `takeover_events`: Audit log of supervisor intervention (`id`, `organization_id`, `call_session_id`, `supervisor_id`, `action`, `notes`, `created_at`).
14. `knowledge_documents`: Verified organizational guides (`id`, `organization_id`, `title`, `document_type`, `status`).
15. `knowledge_chunks`: Searchable plain-text passages (`id`, `document_id`, `organization_id`, `chunk_content`, `chunk_hash`, `metadata`).
16. `agent_configs`: Tenant AI configuration (`id`, `organization_id`, `system_prompt`, `voice_model`, `llm_model`, `temperature`, `is_active`).

---

## 6. Complete REST API Reference

Base URL: `/api/v1`

### 6.1. Health & Diagnostics
- `GET /health/live`: Unauthenticated liveness probe. Returns `{"status": "ok"}`.
- `GET /health/ready`: Unauthenticated readiness probe. Tests database pool connection and provider configuration. Returns:
  ```json
  {
    "status": "ready",
    "version": "0.1.0",
    "environment": "development",
    "database": "connected",
    "livekit": "configured",
    "deepgram": "configured",
    "groq": "configured",
    "timestamp": "2026-10-25T12:00:00Z"
  }
  ```

### 6.2. Customer Voice Endpoints (Unauthenticated / Public)
- `POST /api/v1/voice/token`:
  - **Body**: `{"customer_name": "Sarah Connor", "customer_phone": "+15550192834"}`
  - **Response**: `{"token": "...", "room_name": "epoxa-room-...", "session_id": "...", "livekit_url": "wss://...", "expires_in_seconds": 900}`
- `POST /api/v1/voice/sessions/{session_id}/turn`:
  - **Body**: `{"speech": "What is your refund policy?"}`
  - **Response**: `{"reply": "Our policy allows full returns within 30 days of delivery..."}`
- `POST /api/v1/voice/sessions/{session_id}/end`:
  - Closes the session and generates an automated AI summary.
  - **Response**: `{"id": "...", "status": "completed", "duration_seconds": 142, "summary": {...}}`

### 6.3. Supervisor Endpoints (Requires `Authorization: Bearer <SUPERVISOR_JWT>`)
- `GET /api/v1/auth/me`: Returns current supervisor profile, active organization, and roles.
- `POST /api/v1/auth/dev-token`: Development endpoint to generate a verified local supervisor token.
- `GET /api/v1/calls/active`: Returns all calls in `active`, `escalated`, or `supervisor_takeover` status for the supervisor's organization.
- `GET /api/v1/calls/{session_id}`: Call session details, customer profile, and AI summary.
- `GET /api/v1/calls/{session_id}/transcripts`: Complete chronological speech turns (unpurged).
- `POST /api/v1/calls/{session_id}/takeover`:
  - **Body**: `{"action": "takeover_started", "notes": "Caller requested manager"}`
  - Suppresses AI audio and issues supervisor LiveKit credentials.
- `POST /api/v1/calls/{session_id}/handback`:
  - **Body**: `{"action": "handback_to_ai", "notes": "Return processed"}`
  - Unmutes AI audio and returns session to `active`.

### 6.4. Support Tickets (Requires `Authorization: Bearer <SUPERVISOR_JWT>`)
- `GET /api/v1/tickets?status=open&priority=high&page=1&page_size=20`: Scoped paginated ticket list.
- `POST /api/v1/tickets`: Manually creates a ticket.
  - **Body**: `{"title": "...", "description": "...", "category": "billing", "priority": "urgent"}`
- `GET /api/v1/tickets/{ticket_id}`: Retrieves single ticket details.
- `PATCH /api/v1/tickets/{ticket_id}`: Updates status (`open` ➔ `in_progress` ➔ `resolved` ➔ `closed`), priority, or assigned supervisor.

### 6.5. Customer & Knowledge Endpoints
- `GET /api/v1/customers`: Scoped paginated customer directory.
- `POST /api/v1/customers/lookup`: Finds or verifies a customer by phone number.
- `GET /api/v1/knowledge/search?query=shipping`: Searches FAQ chunks for the tenant.

---

## 7. Environment Variables & Configuration

The application is configured via environment variables or a `.env` file at the repository root.

```bash
# App Configuration
APP_ENV=development                       # 'development' | 'production' | 'test'
APP_NAME=Epoxa
LOG_LEVEL=INFO
FRONTEND_ORIGIN=http://localhost:5173      # CORS allowed origin
BACKEND_BASE_URL=http://localhost:8000

# Database (Supabase PostgreSQL via asyncpg)
DATABASE_URL=postgresql+asyncpg://postgres:your-db-password@your-db-host:5432/postgres

# Supabase Auth
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
SUPABASE_ANON_KEY=your-anon-key

# LiveKit WebRTC Audio Engine
LIVEKIT_URL=wss://your-livekit-host.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret

# Speech Services
DEEPGRAM_API_KEY=your-deepgram-api-key

# LLM Inference (Fast Groq inference by default)
GROQ_API_KEY=your-groq-api-key
OPENAI_API_KEY=your-openai-api-key         # Optional fallback

# Compliance & Retention
TRANSCRIPT_RETENTION_DAYS=30
JWT_EXPECTED_AUDIENCE=authenticated
```

> **Security Mandate**: Frontend clients (`/frontend`) only receive public keys (`SUPABASE_ANON_KEY`, `LIVEKIT_URL`). Database credentials, provider API secrets (`LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `GROQ_API_KEY`), and service keys are strictly isolated to the FastAPI backend.

---

## 8. Operational Commands & Developer Workflows

All routine lifecycle tasks are encapsulated in the root `Makefile`:

| Command | Action | Notes |
|---|---|---|
| `make install` | Installs backend and frontend dependencies | Uses `uv` for python dependencies and `npm install` for frontend |
| `make test` | Runs the full backend test suite | Executes 11 unit & integration tests with Pytest |
| `make migration-target` | Safely inspects the connected database target | Verifies host, port, database, and connection health |
| `make migrate` | Applies Alembic migrations | Runs `alembic upgrade head` |
| `make seed` | Seeds deterministic demo tenant data | Creates Acme Corp demo org, supervisor accounts, FAQs, tickets |
| `make cleanup` | Runs 30-day transcript retention cleanup | Purges/redacts expired transcripts older than 30 days |
| `make run-backend` | Starts FastAPI development server | Runs on `http://127.0.0.1:8000` with auto-reload |
| `make run-frontend` | Starts Vite React frontend development server | Runs on `http://localhost:5173` with proxy to backend |
| `make build-frontend` | Builds production frontend bundle | Compiles TypeScript and creates optimized static bundle |

---

## 9. Current Implementation Status

All core milestones (Phases 1 through 10) are **fully completed, tested, and operational**:
- **Automated Tests**: 11 out of 11 tests passing (`test_tenant_isolation.py`, `test_handoff_state_machine.py`, `test_api_endpoints.py`, `test_seed_demo.py`, `test_retention.py`).
- **Database Schema**: Fully deployed to remote Supabase PostgreSQL 17.11 with initial migration `001_initial_schema`.
- **Demo Seed**: Deterministic demo organization (*Acme Corp*), retail business unit, store location, supervisor profile, sample customer (*Sarah Connor*), knowledge chunks, active/completed call sessions, and support tickets seeded.
- **Frontend**: Cleanly compiles with zero TypeScript errors. Features full customer voice flow with audio visualizer and supervisor dashboard with live call monitoring, interactive takeover, transcript review, and ticket management.

---

## 10. Conventions & Behavioral Rules for AI Assistants

When extending or modifying the Epoxa codebase, adhere to the following rules:

1. **Strict Multi-Tenancy**:
   - Every service and repository function touching customer data, calls, transcripts, or tickets **MUST** accept and filter by `organization_id`.
   - Never query solely by entity ID without appending `AND organization_id = :org_id`.
2. **Asynchronous Database Operations**:
   - Use SQLAlchemy 2.0 asynchronous patterns (`await session.execute(...)`, `scalars().all()`).
   - Do not use synchronous blocking database calls.
3. **No Frontend Secrets**:
   - Never inject backend API keys (`GROQ_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, database connection strings) into frontend bundles or Vite env files.
4. **Structured Logging & Secret Redaction**:
   - Always log using `app.core.logging.logger`.
   - Never log raw authorization tokens, passwords, customer transcripts, or database credentials.
5. **Standardized Error Responses**:
   - Raise `EpoxaException` subclasses (`TenantMismatchException`, `ResourceNotFoundException`, `UnauthorizedException`).
   - The application exception handler will automatically format these into `{ "error": { "message": "...", "correlation_id": "..." } }`.
6. **Git Safety Policy**:
   - The AI agent is **strictly prohibited** from autonomously committing or pushing git changes. All git commits and pushes are executed manually by the user.
