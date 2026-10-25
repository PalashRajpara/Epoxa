"""Off-the-hot-path asynchronous bounded persistence worker for Epoxa Voice Agent."""

import asyncio
from typing import Any, Dict, List, Optional
import structlog
from epoxa_core.database import get_session_factory
from epoxa_core.models.entities import CallTranscript, LatencyLog, CallSession
from sqlalchemy import update

logger = structlog.get_logger("epoxa_agent.persistence")

class AsyncPersistenceWorker:
    """
    Buffers transcript lines, latencies, and session metadata updates off the audio streaming path.
    A database slowdown or temporary failure will NEVER block or drop a live call.
    """

    def __init__(self, max_buffer_size: int = 2000, batch_size: int = 10, flush_interval: float = 1.0) -> None:
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=max_buffer_size)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._running = False
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._session_factory = get_session_factory()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._process_loop(), name="persistence_worker")
        logger.info("persistence_worker_started", buffer_limit=self.queue.maxsize)

    def enqueue_transcript(self, session_id: str, role: str, content: str, sequence: int) -> bool:
        """Enqueue a transcript line. Returns False if buffer is full (never blocks caller)."""
        item = {
            "type": "transcript",
            "session_id": session_id,
            "role": role,
            "content": content,
            "sequence": sequence,
        }
        try:
            self.queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            logger.error("persistence_queue_full_dropped_transcript", session_id=session_id, seq=sequence)
            return False

    def enqueue_latency(self, session_id: str, turn_index: int, durations: Dict[str, int]) -> bool:
        """Enqueue latency records for each measured step."""
        item = {
            "type": "latency",
            "session_id": session_id,
            "turn_index": turn_index,
            "durations": durations,
        }
        try:
            self.queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            logger.error("persistence_queue_full_dropped_latency", session_id=session_id)
            return False

    def enqueue_session_update(self, session_id: str, fields: Dict[str, Any]) -> bool:
        """Enqueue updates to call session record (participant_name, status, room_sid, summary, etc.)."""
        item = {
            "type": "session_update",
            "session_id": session_id,
            "fields": fields,
        }
        try:
            self.queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            logger.error("persistence_queue_full_dropped_update", session_id=session_id)
            return False

    async def _process_loop(self) -> None:
        while self._running or not self.queue.empty():
            batch: List[Dict[str, Any]] = []
            try:
                # Wait for at least one item
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=self.flush_interval)
                    batch.append(item)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    continue

                # Drain up to batch_size items currently in queue
                while len(batch) < self.batch_size and not self.queue.empty():
                    batch.append(self.queue.get_nowait())
                    self.queue.task_done()

                if batch:
                    await self._write_batch_with_retry(batch)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("persistence_worker_error", error=str(e))
                await asyncio.sleep(0.5)

    async def _write_batch_with_retry(self, batch: List[Dict[str, Any]], max_retries: int = 3) -> None:
        retries = 0
        backoff = 0.5
        while retries <= max_retries:
            try:
                async with self._session_factory() as session:
                    async with session.begin():
                        for item in batch:
                            item_type = item.get("type")
                            if item_type == "transcript":
                                t = CallTranscript(
                                    session_id=item["session_id"],
                                    role=item["role"],
                                    content=item["content"],
                                    sequence=item["sequence"],
                                )
                                session.add(t)
                            elif item_type == "latency":
                                session_id = item["session_id"]
                                turn = item["turn_index"]
                                for step, ms in item["durations"].items():
                                    l = LatencyLog(
                                        session_id=session_id,
                                        turn_index=turn,
                                        step=step,
                                        duration_ms=ms,
                                    )
                                    session.add(l)
                            elif item_type == "session_update":
                                stmt = (
                                    update(CallSession)
                                    .where(CallSession.id == item["session_id"])
                                    .values(**item["fields"])
                                )
                                await session.execute(stmt)
                return
            except Exception as e:
                retries += 1
                logger.warning(
                    "persistence_batch_write_failed_retrying",
                    attempt=retries,
                    max_retries=max_retries,
                    error=str(e),
                )
                if retries > max_retries:
                    logger.error("persistence_batch_permanently_failed", batch_size=len(batch), error=str(e))
                    return
                await asyncio.sleep(backoff)
                backoff *= 2

    async def stop(self) -> None:
        """Gracefully stop worker and flush pending items."""
        logger.info("stopping_persistence_worker", pending_items=self.queue.qsize())
        self._running = False
        if self._worker_task:
            try:
                await asyncio.wait_for(self.queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("persistence_queue_flush_timed_out")
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("persistence_worker_stopped")
