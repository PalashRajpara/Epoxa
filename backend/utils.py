"""
backend/utils.py
================
Centralized utilities for logging configuration and latency performance tracking.
Combines app logging, latency logging, and high-precision step timing (STT, LLM, TTS).
"""

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional

# Resolve directories relative to backend root
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file targets
APP_LOG_PATH = os.path.join(LOGS_DIR, "app.log")
LATENCY_LOG_PATH = os.path.join(LOGS_DIR, "latency.log")

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging(level: str = "INFO") -> None:
    """
    Configures console output and file rotating log output.
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

    # Suppress noisier library debug prints
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger("utils.logger")
    logger.info(f"Logging initialized. Level={level}. Log file: {APP_LOG_PATH}")


def get_logger(name: str) -> logging.Logger:
    """
    Retrieves a standard named logger.
    """
    return logging.getLogger(name)


def get_latency_logger() -> logging.Logger:
    """
    Retrieves a special logger mapped directly to logs/latency.log.
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
        console.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        latency_logger.addHandler(console)

    return latency_logger


# =============================================================================
# LATENCY PERFORMANCE TRACKER
# =============================================================================

# General logger and latency-specific rotating file logger
logger = get_logger("utils.latency_tracker")
latency_file_logger = get_latency_logger()

class LatencyTracker:
    """
    Measures duration (in milliseconds) for each voice pipeline step (stt, llm, tts).
    Logs to latency.log and pushes timing metrics to Supabase in the background.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._start_times: Dict[str, float] = {}
        self._results: Dict[str, float] = {}

    def start(self, step: str) -> None:
        """
        Marks high-precision timing start for the specified category.
        """
        self._start_times[step] = time.perf_counter()

    def end(self, step: str) -> Optional[float]:
        """
        Marks timing end, calculates elapsed milliseconds, and logs performance.
        """
        if step not in self._start_times:
            logger.warning(f"[Latency] end('{step}') called without matching start().")
            return None

        elapsed_seconds = time.perf_counter() - self._start_times[step]
        elapsed_ms = elapsed_seconds * 1000.0
        self._results[step] = elapsed_ms
        del self._start_times[step]

        latency_file_logger.info(
            f"[LATENCY] session={self.session_id[:8]}... | step={step:<4} | {elapsed_ms:.1f}ms"
        )

        self._save_to_db(step, elapsed_ms)
        return elapsed_ms

    def _save_to_db(self, step: str, duration_ms: float) -> None:
        """
        Pushes metrics to Supabase. Uses a lazy import to prevent dependency cycles.
        """
        try:
            from database import save_latency_log
            save_latency_log(
                session_id=self.session_id,
                step=step,
                duration_ms=duration_ms,
            )
        except Exception as e:
            logger.error(f"[Latency] Failed to save latency log to Supabase: {e}")

    def print_summary(self) -> None:
        """
        Prints a consolidated summary of STT + LLM + TTS timing.
        """
        if not self._results:
            return

        parts = []
        total_ms = 0.0
        for step in ["stt", "llm", "tts"]:
            if step in self._results:
                ms = self._results[step]
                parts.append(f"{step}={ms:.0f}ms")
                total_ms += ms

        summary_line = " | ".join(parts) + f" | total={total_ms:.0f}ms"
        latency_file_logger.info(f"[LATENCY SUMMARY] session={self.session_id[:8]}... | {summary_line}")

    def get_results(self) -> Dict[str, float]:
        return dict(self._results)

    def reset(self) -> None:
        self._start_times.clear()
        self._results.clear()
