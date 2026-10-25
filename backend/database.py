"""
backend/database.py
===================
Consolidated database layer managing SQLite local tables (for customer details, call session tracking, and transcripts)
and Supabase PostgreSQL cloud sync queries (for call session logging, transcripts, and latency timing).
"""

import sqlite3
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from supabase import create_client, Client

# Resolve SQLite file relative to backend root
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_support.db")

logger = logging.getLogger("backend.database")


# =============================================================================
# SUPABASE CONNECTION HELPER
# =============================================================================

def get_supabase_client() -> Optional[Client]:
    """
    Establishes connection to Supabase via configurations.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return None

    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


# =============================================================================
# CALL SESSIONS OPERATIONS (SQLite + Supabase Sync)
# =============================================================================

def create_call_session(
    session_id: str,
    room_name: str,
    room_sid: Optional[str] = None,
    participant_name: Optional[str] = None,
    customer_id: Optional[int] = None,
) -> bool:
    """
    Inserts a new call session entry into local SQLite and syncs to Supabase if available.
    """
    started_at = datetime.now(timezone.utc).isoformat()

    # 1. Save to local SQLite database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO call_sessions 
               (id, room_name, room_sid, participant_name, customer_id, started_at, status) 
               VALUES (?, ?, ?, ?, ?, ?, 'active')""",
            (session_id, room_name, room_sid, participant_name, customer_id, started_at)
        )
        conn.commit()
        conn.close()
        logger.info(f"[SQLite] Call session created: {session_id}")
    except Exception as sq_err:
        logger.error(f"[SQLite] Failed to create call session: {sq_err}")

    # 2. Try Supabase cloud sync
    client = get_supabase_client()
    if client:
        try:
            data = {
                "id": session_id,
                "room_name": room_name,
                "room_sid": room_sid,
                "participant_name": participant_name,
                "customer_id": customer_id,
                "started_at": started_at,
                "status": "active",
            }
            client.table("call_sessions").insert(data).execute()
            logger.info(f"[Supabase] Call session created: {session_id}")
        except Exception as e:
            logger.warning(f"[Supabase] Failed to create call session (saved to SQLite): {e}")

    return True


def complete_call_session(
    session_id: str,
    status: str,
    duration_seconds: int,
    summary: Optional[str] = None,
    disconnect_reason: Optional[str] = None,
) -> bool:
    """
    Finalizes the call session in SQLite and syncs to Supabase.
    """
    ended_at = datetime.now(timezone.utc).isoformat()

    # 1. Update local SQLite database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE call_sessions 
               SET status = ?, ended_at = ?, duration_seconds = ?, summary = ?, disconnect_reason = ? 
               WHERE id = ?""",
            (status, ended_at, duration_seconds, summary, disconnect_reason, session_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"[SQLite] Call session completed: {session_id} | duration={duration_seconds}s")
    except Exception as sq_err:
        logger.error(f"[SQLite] Failed to update call session: {sq_err}")

    # 2. Try Supabase cloud update
    client = get_supabase_client()
    if client:
        try:
            update_data = {
                "ended_at": ended_at,
                "duration_seconds": duration_seconds,
                "status": status,
            }
            if summary is not None:
                update_data["summary"] = summary
            if disconnect_reason is not None:
                update_data["disconnect_reason"] = disconnect_reason

            client.table("call_sessions").update(update_data).eq("id", session_id).execute()
        except Exception as e:
            logger.warning(f"[Supabase] Failed to update call session: {e}")

    return True


def update_call_session_participant(session_id: str, participant_name: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE call_sessions SET participant_name = ? WHERE id = ?",
            (participant_name, session_id)
        )
        conn.commit()
        conn.close()
    except Exception as sq_err:
        logger.error(f"[SQLite] Failed to update participant_name: {sq_err}")

    client = get_supabase_client()
    if client:
        try:
            client.table("call_sessions").update({"participant_name": participant_name}).eq("id", session_id).execute()
        except Exception as e:
            logger.warning(f"[Supabase] Failed to update participant_name: {e}")
    return True


def update_call_session_room_sid(session_id: str, room_sid: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE call_sessions SET room_sid = ? WHERE id = ?",
            (room_sid, session_id)
        )
        conn.commit()
        conn.close()
    except Exception as sq_err:
        logger.error(f"[SQLite] Failed to update room_sid: {sq_err}")

    client = get_supabase_client()
    if client:
        try:
            client.table("call_sessions").update({"room_sid": room_sid}).eq("id", session_id).execute()
        except Exception as e:
            logger.warning(f"[Supabase] Failed to update room_sid: {e}")
    return True


def get_all_call_sessions() -> List[Dict[str, Any]]:
    """
    Fetches all call sessions, reading from SQLite with Supabase fallback/merge.
    """
    sessions_by_id = {}

    # 1. Read local SQLite sessions
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM call_sessions ORDER BY started_at DESC")
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            d = dict(r)
            sessions_by_id[d["id"]] = d
    except Exception as sq_err:
        logger.error(f"[SQLite] Failed to fetch call sessions: {sq_err}")

    # 2. Merge Supabase cloud sessions if available
    client = get_supabase_client()
    if client:
        try:
            result = (
                client.table("call_sessions")
                .select("*")
                .order("started_at", desc=True)
                .execute()
            )
            if result.data:
                for s in result.data:
                    # Supabase session takes precedence if exists
                    sessions_by_id[s["id"]] = s
        except Exception as e:
            logger.warning(f"[Supabase] Could not fetch sessions from cloud: {e}")

    # Sort descending by started_at
    all_sessions = list(sessions_by_id.values())
    all_sessions.sort(key=lambda x: x.get("started_at") or "", reverse=True)
    return all_sessions


def get_customer_call_history(customer_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches past call log summary for a verified customer.
    """
    sessions = get_all_call_sessions()
    customer_sessions = [s for s in sessions if s.get("customer_id") == customer_id]
    return customer_sessions[:limit]


# =============================================================================
# TRANSCRIPT OPERATIONS (SQLite + Supabase Sync)
# =============================================================================

def save_transcript_entry(
    session_id: str,
    role: str,
    content: str,
    sequence: int,
) -> bool:
    """
    Saves a single transcript turn into local SQLite and syncs to Supabase.
    """
    spoken_at = datetime.now(timezone.utc).isoformat()

    # 1. Save to local SQLite database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO call_transcripts (session_id, role, content, spoken_at, sequence) 
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, role, content, spoken_at, sequence)
        )
        conn.commit()
        conn.close()
        logger.info(f"[SQLite] Saved transcript entry #{sequence} for session {session_id[:8]}")
    except Exception as sq_err:
        logger.error(f"[SQLite] Failed to save transcript turn: {sq_err}")

    # 2. Try Supabase cloud sync
    client = get_supabase_client()
    if client:
        try:
            data = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "spoken_at": spoken_at,
                "sequence": sequence,
            }
            client.table("call_transcripts").insert(data).execute()
        except Exception as e:
            logger.warning(f"[Supabase] Failed to save transcript turn: {e}")

    return True


def get_full_transcript(session_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all transcript turns for a session sorted chronologically.
    Reads from local SQLite first, with Supabase fallback.
    """
    # 1. Try local SQLite database first
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, sequence FROM call_transcripts WHERE session_id = ? ORDER BY sequence",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [dict(r) for r in rows]
    except Exception as sq_err:
        logger.error(f"[SQLite] Failed to fetch transcript list: {sq_err}")

    # 2. Try Supabase cloud database if SQLite is empty
    client = get_supabase_client()
    if client:
        try:
            result = (
                client.table("call_transcripts")
                .select("role, content, sequence")
                .eq("session_id", session_id)
                .order("sequence")
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning(f"[Supabase] Failed to fetch transcript list: {e}")

    return []


def save_latency_log(
    session_id: str,
    step: str,
    duration_ms: float,
) -> bool:
    """
    Inserts a latency log timing metric into Supabase if available.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        data = {
            "session_id": session_id,
            "step": step,
            "duration_ms": duration_ms,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        client.table("latency_logs").insert(data).execute()
        return True
    except Exception as e:
        logger.warning(f"[Supabase] Failed to save latency log: {e}")
        return False


def check_supabase_connection() -> bool:
    """
    Performs a heartbeat check to confirm Supabase connectivity.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        client.table("call_sessions").select("id").limit(1).execute()
        return True
    except Exception as e:
        return False


# =============================================================================
# LOCAL SQLITE DATABASE INITIALIZATION & OPERATIONAL HELPERS
# =============================================================================

def get_db_connection() -> sqlite3.Connection:
    """
    Establishes an active database connection for SQLite.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Creates tables and seeds default values for the SQLite database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create customers profile table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    
    # Create support tickets escalation table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')

    # Create call_sessions table for local tracking & fallback
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS call_sessions (
            id TEXT PRIMARY KEY,
            room_name TEXT NOT NULL,
            room_sid TEXT,
            participant_name TEXT,
            customer_id INTEGER,
            started_at TEXT,
            ended_at TEXT,
            duration_seconds INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            summary TEXT,
            disconnect_reason TEXT
        )
    ''')

    # Create call_transcripts table for local tracking & fallback
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS call_transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            spoken_at TEXT,
            sequence INTEGER NOT NULL
        )
    ''')
    
    conn.commit()
    
    # Seed mock customers if table is empty
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] == 0:
        mock_customers = [
            ("John Doe", "1234567890", "john.doe@example.com", "Premium"),
            ("Alice Smith", "9876543210", "alice.smith@example.com", "Standard"),
            ("Bob Johnson", "5551234567", "bob.johnson@example.com", "Basic")
        ]
        cursor.executemany(
            "INSERT INTO customers (name, phone, email, status) VALUES (?, ?, ?, ?)",
            mock_customers
        )
        conn.commit()
        logger.info("Mock customers seeded inside SQLite database.")
        
    conn.close()


def verify_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a customer profile by their phone number.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, email, status FROM customers WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_support_ticket(customer_id: Optional[int], category: str, description: str) -> int:
    """
    Saves a new customer ticket record.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tickets (customer_id, category, description, status) VALUES (?, ?, ?, 'open')",
        (customer_id, category, description)
    )
    conn.commit()
    ticket_id = cursor.lastrowid
    conn.close()
    return ticket_id


def create_customer(name: str, phone: str, email: str, status: str = "Standard") -> Optional[Dict[str, Any]]:
    """
    Registers a new customer profile.
    """
    cleaned_phone = "".join(char for char in phone if char.isdigit())
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO customers (name, phone, email, status) VALUES (?, ?, ?, ?)",
            (name, cleaned_phone, email, status)
        )
        conn.commit()
        customer_id = cursor.lastrowid
        cursor.execute("SELECT id, name, phone, email, status FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error creating customer in SQLite: {e}")
        return None
    finally:
        conn.close()


def get_all_customers() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, email, status FROM customers")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_tickets() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_id, category, description, status, created_at FROM tickets")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print("Database connection operational. DB located at:", DB_PATH)
