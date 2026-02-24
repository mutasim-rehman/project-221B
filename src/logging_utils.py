"""Safe logging helpers for API and request logging.

These utilities are designed to reduce the chance of leaking secrets or
personally identifiable information (PII) via logs. They avoid logging
environment variables or raw headers, and they truncate or hash user input.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Any, Mapping


REQUEST_LOGGER_NAME = "221b.requests"


def get_request_logger() -> logging.Logger:
    """Return a lazily-configured logger for request/response events."""
    logger = logging.getLogger(REQUEST_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s session=%(session_id)s ip=%(ip)s %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        # Do not propagate to the root logger by default to avoid duplicate logs.
        logger.propagate = False
    return logger


def generate_session_id() -> str:
    """Generate a non-identifying session id suitable for logs."""
    # 128 bits of randomness, rendered as hex.
    return secrets.token_hex(16)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def safe_trim_text(text: str, max_length: int = 512) -> str:
    """Return a truncated representation of user text for logging.

    The full text is not logged; instead, we keep at most `max_length`
    characters plus a short hash so that repeated inputs can be correlated
    without exposing full content.
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    digest = _hash_text(text)
    return f"{text[:max_length]}...[truncated len={len(text)} hash={digest}]"


def log_request(
    logger: logging.Logger,
    *,
    session_id: str,
    user_input: str,
    ip: str | None = None,
    extra_fields: Mapping[str, Any] | None = None,
) -> None:
    """Log a single request in a safe, structured way.

    - User input is truncated and partially hashed.
    - No environment variables or HTTP headers are logged.
    - Session ids and IPs are treated as metadata only.
    """
    safe_text = safe_trim_text(user_input)
    extra: dict[str, Any] = {
        "session_id": session_id,
        "ip": ip or "-",
    }
    if extra_fields:
        # Only include simple scalar values to keep logs compact.
        for k, v in extra_fields.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                extra[k] = v
    logger.info("request text=%s", safe_text, extra=extra)

