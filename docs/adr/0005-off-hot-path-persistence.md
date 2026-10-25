# ADR 0005: Off-the-Hot-Path Asynchronous Persistence Queue

## Status
Accepted

## Context
Writing call transcripts and turn latency logs synchronously inside the voice pipeline loop creates jitter. If the database experiences temporary connection exhaustion or network latency, synchronous writes will delay STT or TTS synthesis, causing audio artifacts, stutter, or dropped calls.

## Decision
1. Implement `AsyncPersistenceWorker` using a bounded in-memory `asyncio.Queue` (buffer capacity: 2000 items).
2. Transcript utterances and latency measurements are pushed onto the queue without waiting (`put_nowait`).
3. A detached background task drains the queue in batches and writes them to PostgreSQL using `epoxa_core` database sessions.
4. Transient database errors are retried with exponential backoff.
5. In the event of a catastrophic database failure, buffer overflow logs an error metric but NEVER drops or pauses the active audio call.
6. The worker cleanly flushes pending items during SIGTERM graceful shutdown.

## Consequences
- Voice streaming audio performance is completely decoupled from database latency.
- Database spikes or slow queries cannot degrade call quality.
