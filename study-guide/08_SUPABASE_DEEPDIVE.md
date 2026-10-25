# 08 — Supabase Deep Dive: Cloud PostgreSQL for Call Telemetry

> SQLite (the local file database) handles customers and tickets.
> Supabase (cloud PostgreSQL) handles call sessions, transcripts, and latency logs.
> This file explains why both exist and how they work together.

---

## What Is Supabase?

Supabase is a "Firebase alternative" — it gives you a hosted PostgreSQL database with extras:
- A web dashboard to browse and manage your data
- Auto-generated REST API (you can query it without writing any backend code)
- Real-time subscriptions (your dashboard can live-update as data comes in)
- Row Level Security (access control at the database level)

**Why Supabase for this project?** The call telemetry data (sessions, transcripts, latency logs)
needs to be:
1. Accessible to the human agent dashboard (React app)
2. Persistent across server restarts
3. Easy to query and visualize
4. Separate from the local SQLite (which only handles sync operations)

**Why not just use SQLite for everything?**
SQLite is a local file — only the process on the same machine can read it easily.
Supabase is a cloud database — any service (agent, backend, dashboard, monitoring tool)
can connect to it from anywhere.

---

## The Three Supabase Tables

These were created by running `backend/schema.sql` in the Supabase SQL editor.

### Table 1: `call_sessions`

One row = one customer support call, from start to finish.

```sql
-- backend/schema.sql

CREATE TABLE IF NOT EXISTS call_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- UUID = Universally Unique Identifier. Looks like "550e8400-e29b-41d4-a716-446655440000".
    -- uuid_generate_v4() auto-generates a random UUID when a row is inserted.
    -- We also generate this UUID in Python (session_id = str(uuid.uuid4())) and pass it in
    -- so both sides know the ID before the database confirms it.

    room_name TEXT NOT NULL,
    -- e.g., "support-user-abc12" — the human-readable LiveKit room name

    room_sid TEXT,
    -- e.g., "RM_xxxxxxxxxxxx" — LiveKit's internal ID for this room session
    -- This is fetched asynchronously after connecting (see main.py background task)

    participant_name TEXT,
    -- The name the customer entered in the frontend (e.g., "John Doe")
    -- Filled in when participant_connected event fires

    customer_id INTEGER,
    -- Links to the customers table in SQLite (if the customer was verified)
    -- NULL if the customer wasn't verified during the call

    started_at TIMESTAMPTZ DEFAULT NOW(),
    -- TIMESTAMPTZ = timestamp with timezone. DEFAULT NOW() fills it automatically.
    ended_at TIMESTAMPTZ,
    -- NULL while the call is active

    duration_seconds INTEGER,
    -- Filled in at call end: int((end_time - start_time).total_seconds())

    status TEXT NOT NULL DEFAULT 'active',
    -- 'active'    = call is currently happening
    -- 'escalated' = human agent has taken over
    -- 'completed' = call ended normally
    -- 'dropped'   = connection was lost
    -- 'timeout'   = customer was silent too long
    -- 'error'     = something crashed

    disconnect_reason TEXT,
    -- Human-readable explanation of why the call ended (for debugging)

    summary TEXT,
    -- 2-3 sentence LLM-generated summary of the call (filled in at end)

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Table 2: `call_transcripts`

One row = one spoken utterance. A 5-minute call might have 40+ rows.

```sql
CREATE TABLE IF NOT EXISTS call_transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    session_id UUID NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE,
    -- REFERENCES call_sessions(id) = foreign key: must match an existing call session
    -- ON DELETE CASCADE = if we delete the call session, delete all its transcripts too

    role TEXT NOT NULL CHECK (role IN ('user', 'agent')),
    -- CHECK constraint: only allow 'user' or 'agent' values
    -- 'user' = customer spoke, 'agent' = AI responded

    content TEXT NOT NULL,
    -- The actual text of what was said

    spoken_at TIMESTAMPTZ DEFAULT NOW(),
    sequence INTEGER NOT NULL DEFAULT 0
    -- Sequence number for ordering (1, 2, 3...) — ensures correct conversation order
);

-- Index: without this, querying "all transcripts for session X" would scan every row.
-- With the index, it's instant even with millions of rows.
CREATE INDEX IF NOT EXISTS idx_call_transcripts_session_id ON call_transcripts(session_id);
```

### Table 3: `latency_logs`

One row = one pipeline step timing. Multiple rows per call (stt, llm, tts for each turn).

```sql
CREATE TABLE IF NOT EXISTS latency_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    session_id UUID NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE,

    step TEXT NOT NULL CHECK (step IN ('stt', 'llm', 'tts')),
    -- 'stt' = how long Deepgram took to transcribe
    -- 'llm' = how long the full LangGraph run took (includes Groq API time)
    -- 'tts' = how long Deepgram took to synthesize and stream audio

    duration_ms FLOAT NOT NULL,
    -- Milliseconds, e.g., 312.5 (about 1/3 second)

    logged_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_latency_logs_session_id ON latency_logs(session_id);
```

---

## The Supabase Python Client — `backend/database.py`

```python
# backend/database.py

from supabase import create_client, Client
import os

def get_supabase_client() -> Optional[Client]:
    """
    Creates and returns a Supabase client.

    We use the SERVICE ROLE key (not the anon key) because:
    - The anon key is for public-facing apps with Row Level Security
    - The service role key bypasses all RLS — gives full database access
    - This is safe because our backend is a server-side process (not the browser)

    Returns None (instead of raising an exception) if credentials aren't configured.
    This enables "graceful degradation" — calls still work even if Supabase is down.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found. "
            "Supabase features are disabled."
        )
        return None  # Don't raise, just return None

    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None
```

---

## Creating a Call Session — `backend/database.py`

```python
# backend/database.py

def create_call_session(
    session_id: str,
    room_name: str,
    room_sid: Optional[str] = None,
    participant_name: Optional[str] = None,
    customer_id: Optional[int] = None,
) -> bool:
    """
    Called at the START of every call.
    Inserts a new row into call_sessions.
    Returns True if successful, False if Supabase is unavailable.
    """
    client = get_supabase_client()
    if not client:
        return False   # Supabase is down, but the call will still work

    try:
        data = {
            "id": session_id,                              # We generate the UUID ourselves
            "room_name": room_name,
            "room_sid": room_sid,                          # None initially (filled in background task)
            "participant_name": participant_name,           # None initially (filled on connect event)
            "customer_id": customer_id,                    # None until customer is verified
            "started_at": datetime.now(timezone.utc).isoformat(),  # Current UTC time as ISO string
            "status": "active",                             # Call just started
        }

        # .insert(data) = INSERT INTO call_sessions (...) VALUES (...)
        # .execute() = actually run the query (Supabase uses a builder pattern)
        client.table("call_sessions").insert(data).execute()
        logger.info(f"[Supabase] Call session created: {session_id}")
        return True

    except Exception as e:
        logger.error(f"[Supabase] Failed to create call session: {e}")
        return False
```

---

## Completing a Call Session — `backend/database.py`

```python
def complete_call_session(
    session_id: str,
    status: str,
    duration_seconds: int,
    summary: Optional[str] = None,
    disconnect_reason: Optional[str] = None,
) -> bool:
    """
    Called at the END of every call.
    Updates the call_sessions row with final data.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        update_data = {
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration_seconds,
            "status": status,                     # "completed", "timeout", "dropped", "error"
        }

        # Conditionally add optional fields
        if summary:
            update_data["summary"] = summary
        if disconnect_reason:
            update_data["disconnect_reason"] = disconnect_reason

        # .update(data) = UPDATE call_sessions SET ...
        # .eq("id", session_id) = WHERE id = session_id
        # .execute() = run it
        client.table("call_sessions").update(update_data).eq("id", session_id).execute()
        logger.info(f"[Supabase] Call session completed: {session_id} ({duration_seconds}s)")
        return True

    except Exception as e:
        logger.error(f"[Supabase] Failed to update call session: {e}")
        return False
```

---

## Saving Transcript Entries — `backend/database.py`

```python
def save_transcript_entry(
    session_id: str,
    role: str,         # "user" or "agent"
    content: str,      # What was said
    sequence: int,     # Order number (1, 2, 3...)
) -> bool:
    """
    Called every time someone finishes speaking.
    In main.py, this is called from the user_speech_committed and
    agent_speech_committed event handlers — both run in the background
    via asyncio.ensure_future() so they never block audio.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        data = {
            "session_id": session_id,                          # Link to parent call
            "role": role,                                      # "user" or "agent"
            "content": content,                                # The text
            "spoken_at": datetime.now(timezone.utc).isoformat(),
            "sequence": sequence,                              # Ordering number
        }
        client.table("call_transcripts").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"[Supabase] Failed to save transcript: {e}")
        return False
```

---

## Fetching the Full Transcript — `backend/database.py`

```python
def get_full_transcript(session_id: str) -> List[Dict[str, Any]]:
    """
    Reads all transcript entries for a call, ordered chronologically.

    Called by:
    1. generate_call_summary() in main.py (to summarize at call end)
    2. share_transcript() in handoff.py (to give context to human agent)
    3. GET /api/rooms/{id}/transcript in routes.py (for the dashboard)
    """
    client = get_supabase_client()
    if not client:
        return []

    try:
        result = (
            client.table("call_transcripts")
            .select("role, content, sequence")      # Only fetch the columns we need
            .eq("session_id", session_id)           # WHERE session_id = ?
            .order("sequence")                      # ORDER BY sequence ASC (chronological)
            .execute()
        )
        return result.data or []
        # result.data is a list of dicts, e.g.:
        # [{"role": "agent", "content": "Hello!", "sequence": 1},
        #  {"role": "user",  "content": "Hi", "sequence": 2}, ...]

    except Exception as e:
        logger.error(f"[Supabase] Failed to fetch transcript: {e}")
        return []
```

---

## Saving Latency Logs — `backend/database.py` and `agent/utils.py`

```python
# backend/database.py
def save_latency_log(session_id: str, step: str, duration_ms: float) -> bool:
    """
    Saves one timing measurement to latency_logs.
    Called from LatencyTracker._save_to_db() in agent/utils.py.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        data = {
            "session_id": session_id,
            "step": step,               # "stt", "llm", or "tts"
            "duration_ms": duration_ms, # e.g., 312.5
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        client.table("latency_logs").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"[Supabase] Failed to save latency log: {e}")
        return False
```

```python
# agent/utils.py — LatencyTracker calls save_latency_log lazily
def _save_to_db(self, step: str, duration_ms: float) -> None:
    try:
        # Lazy import: we only import database when we need it.
        # This avoids circular imports and reduces startup time.
        import sys, os
        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)  # Add backend to path if not already there
        from database import save_latency_log
        save_latency_log(session_id=self.session_id, step=step, duration_ms=duration_ms)
    except Exception as e:
        logger.error(f"[Latency] Failed to save latency log: {e}")
        # Don't re-raise — a latency logging failure should never crash the call
```

---

## The SQLite Local Database — Also in `backend/database.py`

SQLite handles the operational data (customers and tickets):

```python
# backend/database.py

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_support.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    # row_factory = sqlite3.Row makes rows behave like dicts:
    # row["name"] instead of row[1]
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Creates tables and seeds mock data if the DB is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # CREATE TABLE IF NOT EXISTS = create only if it doesn't exist yet
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,  -- UNIQUE prevents duplicate phone numbers
            email TEXT NOT NULL,
            status TEXT NOT NULL        -- "Premium", "Standard", "Basic"
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,         -- Can be NULL for unverified callers
            category TEXT NOT NULL,      -- "Complaint" or "Escalation"
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')

    conn.commit()

    # Seed 3 mock customers if the table is empty
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] == 0:
        mock_customers = [
            ("John Doe",     "1234567890", "john.doe@example.com",    "Premium"),
            ("Alice Smith",  "9876543210", "alice.smith@example.com",  "Standard"),
            ("Bob Johnson",  "5551234567", "bob.johnson@example.com",  "Basic"),
        ]
        # executemany = insert all rows in one efficient batch operation
        cursor.executemany(
            "INSERT INTO customers (name, phone, email, status) VALUES (?, ?, ?, ?)",
            mock_customers
        )
        conn.commit()

    conn.close()
```

---

## Graceful Degradation Pattern

This project is designed so that **Supabase being down doesn't break calls**.
Look at how every database function is structured:

```
1. client = get_supabase_client()     → returns None if not configured
2. if not client: return False        → bail out silently
3. try: ...do the DB work...
4. except Exception: log error, return False
```

And the callers in `main.py`:

```python
session_created = create_call_session(...)
if session_created:
    logger.info("Session created in Supabase")
else:
    logger.warning("Could not create session — calls still work but won't be saved")
# No crash, no exception propagation — the call continues
```

This is "graceful degradation" — the core feature (voice AI) never breaks because of
a logging/monitoring feature being unavailable.

---

*Next up → [10_HANDOFF_AND_ESCALATION.md](./10_HANDOFF_AND_ESCALATION.md)*
