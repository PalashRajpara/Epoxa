# ADR 0003: Server-Authoritative Human Handoff State

## Status
Accepted

## Context
In the legacy implementation, handoff state was stored in an in-memory dictionary `_active_handoffs = {}` inside the agent process. If the agent worker crashed or restarted, handoff state was lost, leading to catastrophic audio overlap where the AI would talk over a human supervisor. Furthermore, takeover and handback trusted client-sent LiveKit data packets without server-side validation or audit logging.

## Decision
1. Persist handoff state authoritatively in `call_sessions.handoff_state` with values:
   - `ai`: AI generates voice turns normally.
   - `human_pending`: Escalation requested; AI is silenced while human joins.
   - `human_active`: Human supervisor has joined room and is speaking.
2. Maintain an in-process memory cache for sub-millisecond audio path checks (`is_ai_silenced`).
3. Supervisor takeover (`POST /api/v1/calls/{id}/takeover`) and handback (`POST /api/v1/calls/{id}/handback`) are server-authoritative API endpoints that write to `handoff_events` and `audit_logs`, update the database, and issue LiveKit server-side signals.

## Consequences
- Survives worker crashes and restarts.
- Full compliance and audit trail of supervisor interventions.
