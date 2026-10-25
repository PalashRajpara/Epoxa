"""
Structured JSON logging using structlog with PII masking and correlation tracking.
All output flows to stdout for container-native log collection.
"""

import logging
import re
import sys
from typing import Any, Dict
import structlog
from epoxa_core.settings import settings


# PII Redaction Regexes
_EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
_PHONE_REGEX = re.compile(r"\+?[1-9]\d{7,14}")
_TOKEN_REGEX = re.compile(r"eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]+")


def mask_pii_string(text: str) -> str:
    """Masks email addresses, phone numbers, and JWT tokens in arbitrary text."""
    if not isinstance(text, str):
        return text
    # Mask JWTs
    text = _TOKEN_REGEX.sub("[REDACTED_JWT]", text)
    # Mask Emails
    text = _EMAIL_REGEX.sub(lambda m: f"{m.group(0)[:2]}***@{m.group(0).split('@')[1]}", text)
    # Mask Phones
    text = _PHONE_REGEX.sub(lambda m: f"{m.group(0)[:3]}***{m.group(0)[-2:]}", text)
    return text


def pii_masking_processor(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor that redacts sensitive PII fields and masks strings."""
    sensitive_keys = {
        "password",
        "secret",
        "token",
        "api_key",
        "access_token",
        "service_role_key",
        "phone",
        "phone_e164",
        "email",
        "content",
    }

    for key, value in list(event_dict.items()):
        if key.lower() in sensitive_keys:
            if isinstance(value, str):
                event_dict[key] = mask_pii_string(value)
            elif key.lower() in {"password", "secret", "token", "api_key", "service_role_key"}:
                event_dict[key] = "[REDACTED]"
        elif isinstance(value, str):
            event_dict[key] = mask_pii_string(value)

    return event_dict


def setup_logging(level: str = "INFO", environment: str = "local") -> None:
    """Configures structlog and the standard library logging system."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        pii_masking_processor,
    ]

    if environment == "local":
        # In local development, use formatted console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # In staging/production, emit pure JSON
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Silence verbose third-party loggers
    for noisy in ["httpx", "httpcore", "urllib3", "asyncio", "livekit"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Returns a structlog logger bound to the given name."""
    return structlog.get_logger(name)
