# Epoxa Database Architecture & Schema Specification
**Project:** Epoxa — Voice AI Agent  
**Author:** Principal Software Architect & PostgreSQL Database Architect  
**Status:** **PENDING HUMAN APPROVAL (Gate Phase B)**  
**Version:** 1.0.0 (Fresh Supabase PostgreSQL Schema)  

---

## 1. Executive Summary & Policy Adherence

In accordance with the mandatory project decisions:
1. **Fresh PostgreSQL Schema:** This is a clean, modern PostgreSQL design for a new dedicated Supabase project. No legacy SQLite application records or existing Supabase records will be imported.
2. **Backend-Only Access:** The React applications (customer app & supervisor dashboard) **never** access database tables directly. All queries and mutations pass strictly through the FastAPI backend (`epoxa_api`).
3. **Supervisor Authentication Authority:** `auth.users` managed by Supabase Auth is the identity authority. Application supervisor profiles link directly to `auth.users(id)` via foreign key.
4. **Version Control:** All database schema objects are managed strictly via **Alembic + SQLAlchemy**, not raw untracked DDL scripts.

---

## 2. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    auth_users ||--o| supervisors : "has profile"
    supervisors ||--o{ tickets : "assigned to"
    supervisors ||--o{ handoff_events : "initiated by"
    
    customers ||--o{ appointments : "books"
    customers ||--o{ tickets : "raises"
    customers ||--o{ call_sessions : "participates in"
    
    call_sessions ||--o{ call_transcripts : "contains"
    call_sessions ||--o{ latency_logs : "records"
    call_sessions ||--o{ handoff_events : "escalates through"
    call_sessions ||--o{ tickets : "originates"

    supervisors {
        uuid id PK "FK auth.users.id"
        varchar email UK "Unique email"
        varchar full_name "Full name"
        varchar role "supervisor | admin"
        boolean is_active "Active status"
        timestamptz created_at
        timestamptz updated_at
    }

    customers {
        uuid id PK "gen_random_uuid()"
        varchar name "Customer full name"
        varchar phone UK "Cleaned 10-15 digits"
        varchar email "Email address"
        varchar status "Standard | Premium | VIP"
        timestamptz created_at
        timestamptz updated_at
    }

    appointments {
        uuid id PK "gen_random_uuid()"
        uuid customer_id FK "REFERENCES customers(id)"
        date appointment_date "Desired date"
        varchar appointment_time "Time string e.g. 2:00 PM"
        varchar confirmation_code UK "e.g. APT-8421"
        varchar status "confirmed | cancelled | completed"
        text notes "Optional notes"
        timestamptz created_at
        timestamptz updated_at
    }

    tickets {
        serial id PK "Human-readable integer ticket ID"
        uuid customer_id FK "REFERENCES customers(id)"
        uuid session_id FK "REFERENCES call_sessions(id)"
        varchar category "Complaint | Escalation | Billing"
        text description "Grievance details"
        varchar status "open | in-progress | resolved | closed"
        uuid assigned_supervisor_id FK "REFERENCES supervisors(id)"
        timestamptz created_at
        timestamptz updated_at
    }

    call_sessions {
        uuid id PK "Call UUID"
        varchar room_name "LiveKit room identifier"
        varchar room_sid "LiveKit internal SID"
        varchar participant_name "Caller display name"
        uuid customer_id FK "REFERENCES customers(id)"
        timestamptz started_at
        timestamptz ended_at
        integer duration_seconds "Call length"
        varchar status "active | escalated | completed | timeout | error"
        text summary "LLM post-call summary"
        varchar disconnect_reason "Reason for call termination"
        timestamptz created_at
    }

    call_transcripts {
        bigserial id PK
        uuid session_id FK "REFERENCES call_sessions(id)"
        varchar role "user | agent | supervisor"
        text content "Utterance text"
        integer sequence "Turn order counter"
        timestamptz spoken_at
    }

    latency_logs {
        uuid id PK "gen_random_uuid()"
        uuid session_id FK "REFERENCES call_sessions(id)"
        varchar step "stt | llm | tts | e2e"
        float duration_ms "Step latency in ms"
        timestamptz logged_at
    }

    handoff_events {
        uuid id PK "gen_random_uuid()"
        uuid session_id FK "REFERENCES call_sessions(id)"
        uuid supervisor_id FK "REFERENCES supervisors(id)"
        varchar action "takeover | return_to_ai | disconnect"
        text notes "Reason / observations"
        timestamptz timestamp
    }
```

---

## 3. Table Inventory & Detailed Schema Specifications

### Table 1: `supervisors`
*Purpose:* Maps authenticated human agents from Supabase Auth (`auth.users`) to application roles and metadata.

| Column | PostgreSQL Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | None | **Primary Key**. References `auth.users(id)` ON DELETE CASCADE. |
| `email` | `VARCHAR(255)` | No | None | **Unique**. Contact email. |
| `full_name` | `VARCHAR(100)` | No | None | Display name of the human agent. |
| `role` | `VARCHAR(50)` | No | `'supervisor'` | Check: `role IN ('supervisor', 'admin')`. |
| `is_active` | `BOOLEAN` | No | `TRUE` | Soft deactivation flag. Inactive agents cannot login or mint tokens. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | Creation timestamp in UTC. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | Last profile update timestamp in UTC. |

---

### Table 2: `customers`
*Purpose:* Durable customer profiles for identification, personalization, and customer history.

| Column | PostgreSQL Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `gen_random_uuid()` | **Primary Key**. UUID prevents enumeration attacks. |
| `name` | `VARCHAR(200)` | No | None | Customer's full name. |
| `phone` | `VARCHAR(20)` | No | None | **Unique**. 10–15 normalized digits (E.164 compatible). |
| `email` | `VARCHAR(255)` | Yes | `NULL` | Customer email address. |
| `status` | `VARCHAR(50)` | No | `'Standard'` | Check: `status IN ('Standard', 'Premium', 'Basic', 'VIP')`. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | Creation timestamp in UTC. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | Last updated timestamp in UTC. |

---

### Table 3: `appointments`
*Purpose:* Persists confirmed appointments scheduled conversationally by Epixa. **(Resolves a critical defect in the previous code where bookings were only mock codes).**

| Column | PostgreSQL Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `gen_random_uuid()` | **Primary Key**. |
| `customer_id` | `UUID` | Yes | `NULL` | Foreign key referencing `customers(id)` ON DELETE SET NULL. |
| `appointment_date`| `DATE` | No | None | Date of the scheduled service. |
| `appointment_time`| `VARCHAR(50)` | No | None | Conversational time (e.g. `'2:00 PM'`, `'10:30 AM'`). |
| `confirmation_code`| `VARCHAR(32)`| No | None | **Unique**. Reference code provided to caller (e.g. `APT-8421`). |
| `status` | `VARCHAR(50)` | No | `'confirmed'` | Check: `status IN ('confirmed', 'cancelled', 'completed', 'rescheduled')`. |
| `notes` | `TEXT` | Yes | `NULL` | Optional details or customer requests. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | Creation timestamp in UTC. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | Update timestamp in UTC. |

---

### Table 4: `tickets`
*Purpose:* Support complaints and customer escalations. Uses an integer primary key so the voice assistant can clearly speak a human-friendly ticket ID (e.g. *"Your ticket number is 42"*).

| Column | PostgreSQL Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | No | Next sequence | **Primary Key**. Consecutive integer for voice readability. |
| `customer_id` | `UUID` | Yes | `NULL` | Foreign key referencing `customers(id)` ON DELETE SET NULL. |
| `session_id` | `UUID` | Yes | `NULL` | Foreign key referencing originating `call_sessions(id)`. |
| `category` | `VARCHAR(100)` | No | None | Check: `category IN ('Complaint', 'Escalation', 'Billing', 'General', 'Technical')`. |
| `description` | `TEXT` | No | None | Customer grievance description (max 2,000 chars validated). |
| `status` | `VARCHAR(50)` | No | `'open'` | Check: `status IN ('open', 'in-progress', 'resolved', 'closed')`. |
| `assigned_supervisor_id` | `UUID` | Yes | `NULL` | Foreign key referencing `supervisors(id)` ON DELETE SET NULL. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | Creation timestamp in UTC. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | Update timestamp in UTC. |

---

### Table 5: `call_sessions`
*Purpose:* Full lifecycle record for each LiveKit voice call session.

| Column | PostgreSQL Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | None | **Primary Key**. Client-generated or session UUID. |
| `room_name` | `VARCHAR(128)` | No | None | LiveKit room name. |
| `room_sid` | `VARCHAR(128)` | Yes | `NULL` | Internal LiveKit Room SID (retrieved asynchronously). |
| `participant_name`| `VARCHAR(200)`| Yes| `NULL` | Display name of the customer. |
| `customer_id` | `UUID` | Yes | `NULL` | Linked verified customer record `customers(id)` ON DELETE SET NULL. |
| `started_at` | `TIMESTAMPTZ` | No | `NOW()` | When caller connected. |
| `ended_at` | `TIMESTAMPTZ` | Yes | `NULL` | When call concluded. |
| `duration_seconds`| `INTEGER` | No | `0` | Call duration; Check: `duration_seconds >= 0`. |
| `status` | `VARCHAR(50)` | No | `'active'` | Check: `status IN ('active', 'escalated', 'completed', 'dropped', 'timeout', 'error')`. |
| `summary` | `TEXT` | Yes | `NULL` | 2–3 sentence LLM post-call summary. |
| `disconnect_reason`| `VARCHAR(255)`| Yes | `NULL` | Human/system reason (e.g. `'participant_disconnected'`, `'timeout'`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | Audit timestamp in UTC. |

---

### Table 6: `call_transcripts`
*Purpose:* Ordered utterance stream between caller, AI agent, and human supervisor.

| Column | PostgreSQL Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `BIGSERIAL` | No | Next sequence | **Primary Key**. |
| `session_id` | `UUID` | No | None | Foreign key referencing `call_sessions(id)` ON DELETE CASCADE. |
| `role` | `VARCHAR(20)` | No | None | Check: `role IN ('user', 'agent', 'supervisor')`. |
| `content` | `TEXT` | No | None | The spoken utterance text. |
| `sequence` | `INTEGER` | No | None | 1-indexed utterance order counter. |
| `spoken_at` | `TIMESTAMPTZ` | No | `NOW()` | Timestamp utterance was committed. |

*Unique Constraint:* `UNIQUE (session_id, sequence)` ensures ordering integrity and eliminates duplicate turns.

---

### Table 7: `latency_logs`
*Purpose:* Discrete turn timing telemetry for performance tracking (STT, LLM, TTS).

| Column | PostgreSQL Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `gen_random_uuid()` | **Primary Key**. |
| `session_id` | `UUID` | No | None | Foreign key referencing `call_sessions(id)` ON DELETE CASCADE. |
| `step` | `VARCHAR(20)` | No | None | Check: `step IN ('stt', 'llm', 'tts', 'e2e')`. |
| `duration_ms` | `DOUBLE PRECISION`| No | None | Duration in ms; Check: `duration_ms >= 0`. |
| `logged_at` | `TIMESTAMPTZ` | No | `NOW()` | Timestamp of turn event. |

---

### Table 8: `handoff_events`
*Purpose:* Audit trail of human supervisor live audio takeovers and hand-backs to the AI.

| Column | PostgreSQL Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `gen_random_uuid()` | **Primary Key**. |
| `session_id` | `UUID` | No | None | Foreign key referencing `call_sessions(id)` ON DELETE CASCADE. |
| `supervisor_id` | `UUID` | Yes | `NULL` | Foreign key referencing `supervisors(id)` ON DELETE SET NULL. |
| `action` | `VARCHAR(50)` | No | None | Check: `action IN ('takeover', 'return_to_ai', 'disconnect')`. |
| `notes` | `TEXT` | Yes | `NULL` | Optional supervisor notes or context. |
| `timestamp` | `TIMESTAMPTZ` | No | `NOW()` | Event timestamp. |

---

## 4. Index Design & Query-Pattern Rationale

| Index Name | Table | Columns | Query Pattern & Justification |
| :--- | :--- | :--- | :--- |
| `idx_customers_phone` | `customers` | `phone` | **UNIQUE B-Tree**. Sub-millisecond caller lookup during voice verification: `WHERE phone = ?`. |
| `idx_appointments_customer` | `appointments` | `customer_id` | Fast lookup of caller appointment history. |
| `idx_appointments_date` | `appointments` | `appointment_date, status` | Schedule view & daily slot verification. |
| `idx_tickets_customer` | `tickets` | `customer_id` | Lookup of existing customer tickets. |
| `idx_tickets_status` | `tickets` | `status, created_at DESC` | Supervisor queue for unassigned/open complaints. |
| `idx_call_sessions_status_started` | `call_sessions` | `status, started_at DESC` | **Crucial:** Optimizes the 3-second dashboard polling query: `WHERE status IN ('active', 'escalated')`. |
| `idx_call_sessions_room` | `call_sessions` | `room_name` | LiveKit room webhook reconciliation. |
| `idx_transcripts_session_seq` | `call_transcripts` | `session_id, sequence ASC` | **Crucial:** Optimizes the 1.5-second live transcript polling query. |
| `idx_latency_session` | `latency_logs` | `session_id` | Post-call telemetry aggregation. |
| `idx_handoff_session` | `handoff_events` | `session_id` | Call escalation history. |

---

## 5. Deletion, Retention, and Invariant Policies

1. **Cascading Deletions:**
   - If a `call_session` is deleted, its `call_transcripts`, `latency_logs`, and `handoff_events` are automatically cascade-deleted (`ON DELETE CASCADE`).
   - If a `customer` is deleted, their associated `call_sessions`, `tickets`, and `appointments` are preserved with `customer_id = NULL` (`ON DELETE SET NULL`) for operational audit integrity.
2. **Data Sanitization & Limits:**
   - Customer phone numbers are normalized to digits-only before storage.
   - Text fields have enforced length limits in Pydantic schemas before reaching PostgreSQL.
3. **Timezones:**
   - Every timestamp column explicitly uses `TIMESTAMPTZ` and defaults to `NOW()`. All application code converts to UTC before persistence.

---

## 6. Row Level Security (RLS) & Access Control Architecture

Even though all application operations flow through the FastAPI backend using server-side pooled credentials:
1. **RLS Enabled Defense-in-Depth:**
   - Every application table will have `ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;`.
   - By default, with no public policies defined, **all direct queries using the Supabase `anon` public key will be rejected (0 rows returned / 403 Forbidden)**.
   - This guarantees that even if a developer or user attempts to query application tables from the browser using the public Supabase URL, no customer data or transcripts can ever be leaked.
2. **Backend Authentication & Authorization:**
   - The FastAPI backend accesses PostgreSQL via SQLAlchemy using a secure connection string.
   - The backend independently verifies Supabase Auth JWTs on every incoming supervisor request and enforces role checks before dispatching queries.

---

## 7. Alembic Migration Implementation Plan

1. **Alembic Layout:**
   - Configuration file: `alembic.ini` (configured to read `DATABASE_URL` dynamically from the environment).
   - Migration environment: `migrations/env.py` (imports `Base.metadata` from `epoxa_core.database.models`).
   - Revision directory: `migrations/versions/`.
2. **Initial Migration:**
   - Revision: `0001_initial_schema.py`
   - Generated and tested against a local disposable PostgreSQL database.
   - Generates all 8 tables, foreign keys, check constraints, and performance indexes.
3. **Safe Workflow Commands:**
   ```bash
   # Check current migration revision
   alembic current

   # Apply pending migrations to the configured database
   alembic upgrade head

   # Verify database is up to date with models
   alembic check
   ```

---

## 8. Fresh Supabase Project Provisioning Instructions

*(To be executed when applying remote schema after design approval)*

1. Log into your [Supabase Dashboard](https://supabase.com/dashboard).
2. Click **New project** (select your organization).
3. Set the Project Name to: **`Epoxa — Voice AI Agent`**.
4. Set a strong database password and select your preferred AWS region.
5. In Project Settings → **Database**:
   - Locate the **Connection string** (URI). Select **Nodejs / Python / SQLAlchemy** format:
     `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
     (Or use Connection Pooling port 6543 for production).
6. In Project Settings → **API**:
   - Copy the **Project URL** (`https://[PROJECT-REF].supabase.co`).
   - Copy the **anon public key**.
   - Copy the **service_role secret key** (for server-side admin user provisioning).
7. In Authentication → **Settings**:
   - Disable "Allow new users to sign up" (Supervisor-only access; new supervisors are created via server-side invitation or admin CLI).
8. Place these credentials securely into your local `.env`.

---

## 9. Review & Approval Gate

> [!IMPORTANT]
> **GATE CHECK: HUMAN APPROVAL REQUIRED**  
> In accordance with Phase B rules, no remote database modifications will occur until this schema design and architecture are reviewed and approved.
