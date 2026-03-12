"""Telemetry decorator for MCP tool calls."""

import logging
import time
from functools import wraps

logger = logging.getLogger("openbrain")

SENSITIVE_KEYS = {"password", "secret", "key", "token", "credential", "authorization"}


def _sanitize_params(kwargs: dict) -> dict:
    sanitized = {}
    for key, value in kwargs.items():
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 100:
            sanitized[key] = value[:100] + "..."
        elif isinstance(value, dict):
            if "narrative" in value and isinstance(value["narrative"], str) and len(value["narrative"]) > 100:
                sanitized[key] = {**value, "narrative": value["narrative"][:100] + "..."}
            else:
                sanitized[key] = value
        else:
            sanitized[key] = value
    return sanitized


def log_tool_call(func):
    """Decorator to log tool entry, exit, duration, and success/failure."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_time = time.time()
        log_params = _sanitize_params(kwargs)

        logger.info(f"Tool called: {tool_name}", extra={"tool_name": tool_name, "parameters": log_params})

        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            has_error = isinstance(result, dict) and "error" in result
            level = logging.WARNING if has_error else logging.INFO
            logger.log(
                level,
                f"Tool completed: {tool_name} ({duration_ms:.0f}ms)",
                extra={"tool_name": tool_name, "duration_ms": duration_ms, "has_error": has_error},
            )
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Tool failed: {tool_name} ({duration_ms:.0f}ms) - {e}",
                extra={"tool_name": tool_name, "duration_ms": duration_ms, "error": str(e)},
            )
            raise

    return wrapper
