"""Latency tracking module for Epoxa Voice Agent turns."""

import time
from typing import Dict, Optional, Callable
import structlog

logger = structlog.get_logger("epoxa_agent.latency")

class LatencyTracker:
    """Tracks latencies for Speech-to-Text (STT), LLM generation, and Text-to-Speech (TTS)."""

    def __init__(self, session_id: str, on_turn_complete: Optional[Callable[[Dict[str, int]], None]] = None) -> None:
        self.session_id = session_id
        self.on_turn_complete = on_turn_complete
        self.turn_index = 0
        self._start_times: Dict[str, float] = {}
        self._durations: Dict[str, int] = {}

    def reset(self) -> None:
        """Reset step timers for a new conversational turn."""
        self.turn_index += 1
        self._start_times.clear()
        self._durations.clear()

    def start(self, step: str) -> None:
        """Start timing a step ('stt', 'llm', 'tts', 'e2e')."""
        self._start_times[step] = time.perf_counter()

    def end(self, step: str) -> Optional[int]:
        """End timing a step and return duration in milliseconds."""
        start = self._start_times.get(step)
        if start is None:
            return None
        duration_ms = max(0, int((time.perf_counter() - start) * 1000))
        self._durations[step] = duration_ms
        return duration_ms

    def record_e2e(self) -> None:
        """Calculate and store end-to-end turn latency."""
        stt = self._durations.get("stt", 0)
        llm = self._durations.get("llm", 0)
        tts = self._durations.get("tts", 0)
        self._durations["e2e"] = stt + llm + tts

        logger.info(
            "turn_latency_measured",
            session_id=self.session_id,
            turn=self.turn_index,
            stt_ms=stt,
            llm_ms=llm,
            tts_ms=tts,
            e2e_ms=self._durations["e2e"],
        )

        if self.on_turn_complete:
            try:
                self.on_turn_complete(dict(self._durations))
            except Exception as e:
                logger.warning("failed_latency_callback", error=str(e))

    def get_durations(self) -> Dict[str, int]:
        return dict(self._durations)
