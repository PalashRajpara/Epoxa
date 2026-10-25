"""Test suite for AsyncPersistenceWorker off-the-hot-path buffering."""

import pytest
from epoxa_agent.persistence import AsyncPersistenceWorker

def test_enqueue_non_blocking() -> None:
    worker = AsyncPersistenceWorker(max_buffer_size=5)
    # Enqueuing does not block and returns True when buffer has space
    for i in range(5):
        assert worker.enqueue_transcript("test-session", "user", f"hello {i}", i) is True

    # Buffer full returns False without raising exception or dropping audio
    assert worker.enqueue_transcript("test-session", "user", "overflow", 6) is False
