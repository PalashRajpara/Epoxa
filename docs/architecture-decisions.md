# Epoxa Architecture Decision Records (ADRs)

## ADR-001: Modular Monolith vs. Microservices
- **Status**: Accepted
- **Context**: Epoxa V1 requires low operational complexity, high developer velocity, and robust transactional consistency across calls, tickets, and takeovers.
- **Decision**: Build Epoxa as a modular monolith in FastAPI + React.
- **Consequences**: Avoids distributed transaction overhead, network latency between microservices, and complex container orchestration while maintaining strict layer boundaries.

## ADR-002: LiveKit for Real-Time WebRTC Media Transport
- **Status**: Accepted
- **Context**: Voice customer support requires low-latency bi-directional audio streaming, room management, participant state monitoring, and live supervisor takeover (adding an agent into an ongoing room).
- **Decision**: Adopt LiveKit as the WebRTC media engine. The backend acts as the authorization controller issuing room-scoped, short-lived tokens.
- **Consequences**: Eliminates complex custom WebRTC signaling infrastructure. Client never accesses LiveKit API secrets directly.

## ADR-003: Deepgram for STT and TTS
- **Status**: Accepted
- **Context**: Voice conversations demand sub-300ms speech-to-text transcription and ultra-fast, natural-sounding voice synthesis (Deepgram Nova-2 / Aura).
- **Decision**: Integrate Deepgram behind provider adapter interfaces (`app.integrations.speech`).
- **Consequences**: Standardized adapter pattern enables swapping or mocking speech providers during local testing without touching business logic.

## ADR-004: Supabase PostgreSQL with SQLAlchemy 2.0 & Alembic
- **Status**: Accepted
- **Context**: Persistent application data needs rock-solid relational consistency, ACID guarantees for ticket state machines, and support for automated migrations.
- **Decision**: Supabase PostgreSQL is the sole durable data store. Alembic manages all schema revisions. No dual-writing to SQLite.
- **Consequences**: Safe schema evolution, repeatable migrations, and single source of truth.

## ADR-005: 30-Day Automated Transcript Retention Policy
- **Status**: Accepted
- **Context**: Privacy regulations (GDPR/CCPA) and data minimization guidelines require limiting customer voice transcript persistence.
- **Decision**: Transcripts are stored in a dedicated `transcripts` table and purged/redacted after 30 days via an automated, idempotent CLI/scheduled job. Call metadata, duration, and objective summaries remain intact.
- **Consequences**: Enforces compliance while preserving operational metrics and ticket context.
