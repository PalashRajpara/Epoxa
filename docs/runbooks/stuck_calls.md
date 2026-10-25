# Runbook: Resolving Stuck or Stale Call Sessions

## Symptoms
- A call session remains in `status='active'` or `status='escalated'` long after both participants have left the browser.
- Live queue shows ghost calls with zero active WebRTC audio packets.

---

## 1. Automated Background Reconciliation
Epoxa includes an automated background worker (`epoxa_api.background.reconciliation`) that runs every 30 seconds protected by an advisory lock:
1. Queries all active sessions in the database.
2. Queries the LiveKit Server API to verify if the corresponding room exists and has active participants.
3. If a room has 0 participants, it observes a **60-second grace period** (INVARIANT 5) to allow momentary customer network reconnects.
4. If still vacant after 60 seconds, it automatically marks the session `status='dropped'` or `status='completed'` with `end_reason='reconciled_stale_session'`.

---

## 2. Manual Supervisor Termination
If a session is hung due to LiveKit webhook delays:
1. Log into the Supervisor Console (`/calls`).
2. Select the hung session from the queue.
3. Click **"End Call"** in the upper-right actions plate.
4. Confirm the prompt:
   - FastAPI calls `LiveKit Server API` to close the room.
   - Updates `call_sessions.status = 'completed'` and `ended_at = NOW()`.
   - Flushes transcript buffer.

---

## 3. Emergency Database Cleanup
If the LiveKit API is unreachable during an outage:
```sql
UPDATE public.call_sessions
SET 
    status = 'dropped',
    ended_at = NOW(),
    end_reason = 'manual_admin_cleanup',
    duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::int
WHERE 
    status IN ('active', 'escalated')
    AND started_at < NOW() - INTERVAL '30 minutes';
```
