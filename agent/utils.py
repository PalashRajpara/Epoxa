"""
agent/utils.py
==============
Logging helpers and latency tracking for the agent process.
Provides setup_logging(), get_logger(), and LatencyTracker
so all agent utilities live in one flat file.
"""

import os
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional

# Resolve the logs directory relative to this file (agent/../logs)
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

APP_LOG_PATH = os.path.join(LOGS_DIR, "app.log")
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """
    Configures console and rotating file log output for the agent process.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    file_handler = RotatingFileHandler(
        APP_LOG_PATH,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    logging.basicConfig(
        level=numeric_level,
        handlers=[console_handler, file_handler],
        force=True
    )

    # Suppress noisy library debug prints
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.getLogger("agent.utils").info(
        f"Logging initialized. Level={level}. Log file: {APP_LOG_PATH}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Returns a standard named logger instance.
    """
    return logging.getLogger(name)


# =============================================================================
# LATENCY LOGGER — writes to logs/latency.log
# =============================================================================

LATENCY_LOG_PATH = os.path.join(LOGS_DIR, "latency.log")


def get_latency_logger() -> logging.Logger:
    """
    Returns a dedicated logger that writes only to logs/latency.log.
    """
    latency_logger = logging.getLogger("latency")
    if not latency_logger.handlers:
        latency_logger.setLevel(logging.INFO)
        latency_logger.propagate = False

        handler = RotatingFileHandler(
            LATENCY_LOG_PATH,
            maxBytes=2 * 1024 * 1024,  # 2 MB
            backupCount=5,
            encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        latency_logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(
            "[%(asctime)s] %(message)s", datefmt="%H:%M:%S"
        ))
        latency_logger.addHandler(console)

    return latency_logger


# =============================================================================
# LATENCY TRACKER — high-precision STT / LLM / TTS timing
# =============================================================================

_latency_file_logger = get_latency_logger()
_tracker_logger = get_logger("utils.latency_tracker")


class LatencyTracker:
    """
    Measures duration (in milliseconds) for each voice pipeline step (stt, llm, tts).
    Logs to latency.log and optionally pushes timing metrics to Supabase.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._start_times: Dict[str, float] = {}
        self._results: Dict[str, float] = {}

    def start(self, step: str) -> None:
        """Marks high-precision timing start for the specified category."""
        self._start_times[step] = time.perf_counter()

    def end(self, step: str) -> Optional[float]:
        """Marks timing end, calculates elapsed milliseconds, and logs performance."""
        if step not in self._start_times:
            _tracker_logger.warning(f"[Latency] end('{step}') called without matching start().")
            return None

        elapsed_ms = (time.perf_counter() - self._start_times[step]) * 1000.0
        self._results[step] = elapsed_ms
        del self._start_times[step]

        _latency_file_logger.info(
            f"[LATENCY] session={self.session_id[:8]}... | step={step:<4} | {elapsed_ms:.1f}ms"
        )
        self._save_to_db(step, elapsed_ms)
        return elapsed_ms

    def _save_to_db(self, step: str, duration_ms: float) -> None:
        """Pushes metrics to Supabase via lazy import to prevent dependency cycles."""
        try:
            import sys, os
            backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            from database import save_latency_log
            save_latency_log(session_id=self.session_id, step=step, duration_ms=duration_ms)
        except Exception as e:
            _tracker_logger.error(f"[Latency] Failed to save latency log: {e}")

    def print_summary(self) -> None:
        """Prints a consolidated summary of STT + LLM + TTS timing."""
        if not self._results:
            return
        parts = []
        total_ms = 0.0
        for step in ["stt", "llm", "tts"]:
            if step in self._results:
                ms = self._results[step]
                parts.append(f"{step}={ms:.0f}ms")
                total_ms += ms
        summary = " | ".join(parts) + f" | total={total_ms:.0f}ms"
        _latency_file_logger.info(
            f"[LATENCY SUMMARY] session={self.session_id[:8]}... | {summary}"
        )

    def get_results(self) -> Dict[str, float]:
        return dict(self._results)

    def reset(self) -> None:
        self._start_times.clear()
        self._results.clear()
