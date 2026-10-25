"""Test suite for escalation regex including false-positive and negative cases."""

import pytest
from epoxa_agent.nodes import is_escalation_intent

@pytest.mark.parametrize(
    "phrase",
    [
        "I need to speak to a human right now",
        "Please talk to a human",
        "transfer me",
        "Transfer me to a representative",
        "can you connect me to a human please",
        "I want a supervisor immediately",
        "speak to an agent",
        "hand me over",
        "handover to manager",
        "i want a human",
    ],
)
def test_escalation_positive_matches(phrase: str) -> None:
    assert is_escalation_intent(phrase) is True

@pytest.mark.parametrize(
    "phrase",
    [
        "That is superhuman speed",
        "The humanity is facing great challenges",
        "I love this AI assistant",
        "What are your opening hours?",
        "Can I book an appointment for tomorrow?",
        "I want to know about your services",
        "Where is your office located?",
    ],
)
def test_escalation_negative_cases(phrase: str) -> None:
    assert is_escalation_intent(phrase) is False
