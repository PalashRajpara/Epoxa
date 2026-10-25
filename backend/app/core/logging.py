import logging
import sys
import structlog
from typing import Any

def setup_logging(log_level: str = "INFO") -> structlog.stdlib.BoundLogger:
    """Configures structured JSON logging with security redactions."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Standard python logging configuration
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    def censor_sensitive_keys(logger: Any, method_name: str, event_dict: dict) -> dict:
        """Censors tokens, passwords, and authorization headers from logs."""
        sensitive_keys = {
            "password", "secret", "token", "access_token", "api_key",
            "authorization", "cookie", "transcript", "content"
        }
        for k, v in list(event_dict.items()):
            if any(s in k.lower() for s in sensitive_keys):
                if isinstance(v, str) and len(v) > 8:
                    event_dict[k] = f"{v[:2]}...[REDACTED]"
                else:
                    event_dict[k] = "[REDACTED]"
        return event_dict

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            censor_sensitive_keys,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("epoxa")

logger = setup_logging()
