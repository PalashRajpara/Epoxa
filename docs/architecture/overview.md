# Epoxa: Production Architecture & System Specification

**Product:** Epoxa Real-Time Voice AI Agent & Supervisor Console  
**Organization:** Epoxcel  
**Agent Persona:** Epixa  
**Status:** Production Launch-Ready Architecture  

---

## 1. System Overview

Epoxa is an enterprise-grade real-time Voice AI agent platform providing natural speech interactions for inbound customer service, appointment scheduling, grievance registration, and real-time supervisor escalation with human takeover.

### Key Architectural Pillars
1. **Clean Modular Monorepo:** Structured using `uv` (Python 3.12) and `pnpm` (TypeScript) workspaces. Repositories and domain logic live in `packages/core`, strictly consumed by `apps/api` and `apps/agent`. No circular dependencies or `sys.path` hacks.
2. **PostgreSQL Relational Single Source of Truth:** 12 normalized tables versioned with Alembic, featuring database-level triggers, Row Level Security (RLS) enforced across all tables, and least-privilege roles (`epoxa_api`, `epoxa_agent`, `epoxa_migrator`).
3. **Stateless Voice Agent Workers:** Vector similarity search powered by `pgvector` (`kb_chunks` with HNSW cosine index) and in-memory caching, replacing local file-based ChromaDB.
4. **Off-the-Hot-Path Persistence:** Real-time speech transcription and latency measurements are buffered via a bounded asynchronous queue, guaranteeing that database write latencies never degrade live WebRTC audio streams.
5. **Server-Authoritative Escalation & Handoff:** Call states (`ai`, `human_pending`, `human_active`) are authoritatively tracked in PostgreSQL with append-only audit logging and WebRTC track isolation.
6. **Supervisor RBAC & Auth:** Secured via Supabase Auth asymmetric JWKS JWT verification. Public endpoints are rate-limited with concurrent call caps.

---

## 2. C4 Architecture Diagrams

### 2.1 System Context Diagram (C4 Level 1)
```mermaid
C4Context
    title System Context Diagram - Epoxa Voice AI Platform

    Person(caller, "Customer / Caller", "Interacts via browser WebRTC microphone to book appointments or seek assistance.")
    Person(supervisor, "Supervisor / Admin", "Monitors live calls, views real-time transcripts, takes over escalations.")

    System(epoxa, "Epoxa Platform", "Real-time voice AI orchestration, automated booking, ticketing, and escalation.")

    System_Ext(livekit, "LiveKit Cloud", "Low-latency WebRTC SFU streaming audio packets and data messages.")
    System_Ext(deepgram, "Deepgram", "Nova-2 Speech-to-Text (STT) and Aura streaming Text-to-Speech (TTS).")
    System_Ext(groq, "Groq Cloud", "Ultra-low-latency Llama 3.1 LLM inference for dialogue management.")
    System_Ext(supabase, "Supabase", "Managed PostgreSQL database with pgvector, Auth identity provider, and connection pooler.")

    Rel(caller, epoxa, "Initiates call, speaks, listens", "WebRTC / HTTPS")
    Rel(supervisor, epoxa, "Authenticates, monitors live SSE, intervenes", "HTTPS / WSS")
    Rel(epoxa, livekit, "WebRTC audio tracks & data packets", "WSS")
    Rel(epoxa, deepgram, "Audio streaming for STT & TTS", "WSS / HTTPS")
    Rel(epoxa, groq, "LLM prompt completion & extraction", "HTTPS")
    Rel(epoxa, supabase, "JWKS auth validation, pooled SQL queries", "TCP 6543 / 5432")
```

### 2.2 Container Diagram (C4 Level 2)
```mermaid
C4Container
    title Container Diagram - Epoxa Monorepo

    Container(web, "Customer Web App", "Vite, React 18, TS", "Provides microphone interface, animated voice orb visualizer, and call initiation.")
    Container(dashboard, "Supervisor Dashboard", "Vite, React 18, TS", "Provides Supabase Auth login, live SSE call monitoring, takeover controls, and ticket management.")

    Container(api, "FastAPI Service (epoxa_api)", "FastAPI, Python 3.12", "Exposes REST endpoints, validates Supabase JWTs, mints restricted tokens, streams live SSE, runs retention jobs.")
    Container(agent, "Voice Agent Worker (epoxa_agent)", "LiveKit Agents, LangGraph", "Long-lived worker orchestrating Silero VAD, Deepgram STT/TTS, and LangGraph dialogue nodes.")

    Container(core, "Core Domain Library (epoxa_core)", "SQLAlchemy 2.0, Pydantic v2", "Shared domain models, async repositories, Unit of Work, settings, and structured JSON logging.")
    ContainerDb(db, "Supabase PostgreSQL Database", "PostgreSQL 16, pgvector", "Stores organizations, profiles, memberships, customers, sessions, transcripts, appointments, and vector embeddings.")

    Rel(web, api, "POST /api/v1/calls (public, rate-limited)", "HTTPS")
    Rel(web, agent, "WebRTC Audio stream via LiveKit SFU", "WSS")

    Rel(dashboard, api, "REST & SSE /api/v1/calls/stream", "HTTPS (Bearer JWT)")
    Rel(dashboard, agent, "Audio takeover via LiveKit SFU", "WSS")

    Rel(api, core, "Invokes domain services & UoW", "Internal Package")
    Rel(agent, core, "Invokes domain services & persistence", "Internal Package")

    Rel(core, db, "Async SQL via Supavisor pooler", "TCP / TLS")
```

---

## 3. High-Level Call Flow & Escalation Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Customer (Browser)
    participant API as FastAPI Backend (/api/v1)
    participant LK as LiveKit Cloud
    participant Agent as Epixa Agent Worker
    participant DB as PostgreSQL (Supabase)
    actor Supervisor as Supervisor Dashboard

    Customer->>API: POST /api/v1/calls { participant_name, phone }
    API->>DB: INSERT call_sessions (status='active', handoff_state='ai')
    API->>LK: Mint short-lived customer token (audio-only, room bound)
    API-->>Customer: Return { session_id, room_name, token, livekit_url }

    Customer->>LK: Connect to room & publish microphone track
    LK->>Agent: Dispatch job for room
    Agent->>LK: Connect to room (AUDIO_ONLY)
    Agent->>Customer: "Hello! Welcome to Epoxcel. My name is Epixa..."

    Customer->>Agent: "I want to speak with a human representative."
    Agent->>Agent: Regex detects escalation keyword boundary
    Agent->>DB: INSERT tickets (category='Escalation', priority='urgent')
    Agent->>DB: UPDATE call_sessions (handoff_state='human_pending')
    Agent->>Customer: "I am transferring you to a human agent now. Please hold."

    API-->>Supervisor: SSE Stream emits handoff_state='human_pending'
    Supervisor->>API: POST /api/v1/calls/{id}/takeover
    API->>DB: INSERT handoff_events (action='takeover')
    API->>DB: UPDATE call_sessions (handoff_state='human_active')
    API->>LK: Mint supervisor token
    API-->>Supervisor: Return supervisor room token

    Supervisor->>LK: Connect & publish microphone track
    Agent->>Agent: Track subscribed from 'agent_*' -> Unsubscribe immediately (Audio Isolation)
    Supervisor->>Customer: "Hello, this is human support. I am taking over your call."

    Supervisor->>API: POST /api/v1/calls/{id}/handback
    API->>LK: Send Data Packet { action: 'resume' }
    API->>DB: UPDATE call_sessions (handoff_state='ai')
    Agent->>Customer: "Welcome back! I'm back on the line. How can I help you resolve the rest of your issue?"
```

---

## 4. Voice Pipeline Invariants (Non-Negotiable)

1. **Non-Blocking `room.sid`:** LiveKit's `ctx.room.sid` is awaited inside a detached background task (`asyncio.create_task`). It must never block agent startup or greeting playback.
2. **Multi-Participant Track Isolation:** Audio tracks from participants starting with `agent_` or `human_` are immediately unsubscribed (`publication.set_subscribed(False)`), preventing audio echo and acoustic interference.
3. **DOM Audio Element Attachment:** In the React client, `track.attach()` elements are explicitly appended to `document.body` to prevent browser garbage collection of the audio context.
4. **Word-Boundary Escalation Detection:** Regex `\b(speak to a human|talk to a human|transfer me|...)\b` prevents false-positives on words like "superhuman" or general conversational mentions.
5. **Calibrated Pipeline Latency Timings:**
   - `interrupt_speech_duration = 0.7s`
   - `interrupt_min_words = 2`
   - `min_endpointing_delay = 0.6s`
   - `preemptive_synthesis = False`
