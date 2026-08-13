-- =============================================================================
-- Phase 3: Supabase PostgreSQL Schema
-- =============================================================================
-- HOW TO USE THIS FILE:
--   1. Go to your Supabase project → SQL Editor
--   2. Paste this entire file and click "Run"
--   3. That's it! All 3 tables will be created.
-- =============================================================================

-- Enable the uuid-ossp extension so we can generate UUIDs automatically.
-- UUIDs are unique IDs that look like: "550e8400-e29b-41d4-a716-446655440000"
-- They are better than auto-increment integers for distributed systems because
-- you can generate them anywhere without needing to check the database first.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- =============================================================================
-- TABLE 1: call_sessions
-- One row is created per call. It tracks the whole call from start to finish.
-- =============================================================================
CREATE TABLE IF NOT EXISTS call_sessions (
    -- id: A unique identifier for this call, auto-generated as a UUID.
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- room_name: The LiveKit room name (e.g., "support-abc12").
    -- This is the human-readable name the frontend uses.
    room_name TEXT NOT NULL,

    -- room_sid: LiveKit's internal unique identifier for the room.
    -- SID = Session Identifier. This is different from room_name.
    -- Example: "RM_xxxxxxxxxxxx"
    room_sid TEXT,

    -- participant_name: The name the customer typed in when they joined.
    participant_name TEXT,

    -- customer_id: If the customer was verified by phone number during the call,
    -- this links to their record in your SQLite customers table.
    -- It's nullable (INTEGER) because not every caller gets verified.
    customer_id INTEGER,

    -- started_at: The exact date and time the call began.
    -- DEFAULT NOW() means Supabase will fill this in automatically.
    -- "timestamptz" means it stores timezone information too.
    started_at TIMESTAMPTZ DEFAULT NOW(),

    -- ended_at: When the call ended. NULL means the call is still active.
    ended_at TIMESTAMPTZ,

    -- duration_seconds: How long the call lasted, calculated at the end.
    duration_seconds INTEGER,

    -- status: The current state of this call.
    -- Possible values: 'active', 'completed', 'dropped', 'error'
    -- 'active'    = call is currently in progress
    -- 'completed' = call ended normally (customer hung up)
    -- 'dropped'   = customer's connection was lost unexpectedly
    -- 'error'     = something went wrong on our end
    status TEXT NOT NULL DEFAULT 'active',

    -- disconnect_reason: Why the call ended. Only filled in if it wasn't normal.
    -- Example: "participant_disconnected", "timeout", "api_error"
    disconnect_reason TEXT,

    -- summary: A 2-3 sentence LLM-generated summary of what happened in the call.
    -- Filled in at the end of the call. NULL until the call ends.
    summary TEXT,

    -- created_at: When this database row was created (for auditing purposes).
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add a comment to describe this table (visible in Supabase dashboard)
COMMENT ON TABLE call_sessions IS 'Tracks each customer support call from start to finish. One row per call.';


-- =============================================================================
-- TABLE 2: call_transcripts
-- One row per spoken message in a call. This is the full conversation log.
-- =============================================================================
CREATE TABLE IF NOT EXISTS call_transcripts (
    -- id: Unique identifier for this single utterance/message.
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- session_id: Which call does this message belong to?
    -- REFERENCES call_sessions(id) means this must match an existing call.
    -- ON DELETE CASCADE means: if we delete a call, delete all its transcript lines too.
    session_id UUID NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE,

    -- role: Who said this? Either 'user' (customer) or 'agent' (AI assistant).
    role TEXT NOT NULL CHECK (role IN ('user', 'agent')),

    -- content: The actual text of what was said.
    content TEXT NOT NULL,

    -- spoken_at: When this was said.
    spoken_at TIMESTAMPTZ DEFAULT NOW(),

    -- sequence: The order this message appeared in the conversation.
    -- 1 = first message, 2 = second message, etc.
    -- This lets us reconstruct the conversation in the right order.
    sequence INTEGER NOT NULL DEFAULT 0,

    -- created_at: When this row was saved to the database.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index: Makes it fast to look up all transcripts for a specific call.
-- Without this index, the database would have to scan every row to find them.
CREATE INDEX IF NOT EXISTS idx_call_transcripts_session_id ON call_transcripts(session_id);

COMMENT ON TABLE call_transcripts IS 'Stores every utterance (user and agent) in a call, in order.';


-- =============================================================================
-- TABLE 3: latency_logs
-- One row per pipeline step timing. Tells us how fast each part of the AI is.
-- =============================================================================
CREATE TABLE IF NOT EXISTS latency_logs (
    -- id: Unique identifier for this timing measurement.
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- session_id: Which call did this measurement belong to?
    session_id UUID NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE,

    -- step: Which part of the pipeline was measured?
    -- 'stt' = Speech-to-Text (Deepgram converting voice to text)
    -- 'llm' = Language Model (Groq/LangGraph generating a response)
    -- 'tts' = Text-to-Speech (Deepgram converting text to voice)
    step TEXT NOT NULL CHECK (step IN ('stt', 'llm', 'tts')),

    -- duration_ms: How long this step took in milliseconds.
    -- Example: 342.5 means it took 342.5 milliseconds (about 1/3 of a second).
    duration_ms FLOAT NOT NULL,

    -- logged_at: When this measurement was taken.
    logged_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index: Makes it fast to look up all latency logs for a specific call.
CREATE INDEX IF NOT EXISTS idx_latency_logs_session_id ON latency_logs(session_id);

COMMENT ON TABLE latency_logs IS 'Records how long each pipeline step (STT, LLM, TTS) takes per call turn.';


-- =============================================================================
-- DONE! 
-- After running this, go to Supabase → Table Editor to confirm all 3 tables exist.
-- =============================================================================
