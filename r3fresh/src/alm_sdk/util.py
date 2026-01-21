# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Utility functions for ALM SDK."""
import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import uuid4


def utc_now_iso() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


def safe_error(e: Exception) -> Dict[str, str]:
    """Return a safe error representation without huge stack traces."""
    return {
        "type": type(e).__name__,
        "message": str(e),
    }


def create_structured_error(
    exception: Exception,
    source: str = "tool",
    code: Optional[str] = None,
    retryable: Optional[bool] = None,
) -> Dict[str, Any]:
    """Create a structured error object from an exception.

    Args:
        exception: The exception to convert
        source: Source of error (tool, policy, agent, system)
        code: Optional error code
        retryable: Whether error is retryable (auto-detected if None)

    Returns:
        Structured error dictionary
    """
    error_type = type(exception).__name__
    error_message = str(exception)

    # Auto-detect retryable errors if not specified
    if retryable is None:
        retryable_errors = {
            "ConnectionError",
            "TimeoutError",
            "TemporaryFailure",
            "RateLimitError",
            "ServiceUnavailableError",
        }
        retryable = error_type in retryable_errors or "timeout" in error_message.lower()

    error_dict: Dict[str, Any] = {
        "type": error_type,
        "message": error_message,
        "source": source,
        "retryable": retryable,
    }

    if code:
        error_dict["code"] = code

    return error_dict


def redact_sensitive(value: Any, max_length: int = 1000) -> Any:
    """Redact sensitive information from values.

    - Truncate long strings
    - Mask sensitive keys
    """
    if isinstance(value, str):
        if len(value) > max_length:
            return value[:max_length] + "... (truncated)"
        return value
    if isinstance(value, dict):
        redacted = {}
        sensitive_keys = {"password", "token", "api_key", "apikey", "secret", "key"}
        for k, v in value.items():
            key_lower = k.lower()
            # Check if key contains any sensitive keywords
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = redact_sensitive(v, max_length)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item, max_length) for item in value]
    return value


def normalize_args(func: Callable, args: tuple, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize function arguments to a dict of parameter names to values.

    Binds positional args to their parameter names for better analytics/search.
    Falls back to keeping args/kwargs structure if binding fails.

    Args:
        func: The function to bind arguments to
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Dict with normalized arguments (either {"inputs": {...}} or {"args": [...], "kwargs": {...}})
    """
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        # Return normalized dict with parameter names
        return {"inputs": dict(bound.arguments)}
    except (TypeError, AttributeError):
        # If binding fails (e.g., built-in functions, complex signatures), fall back to original
        return {
            "args": list(args) if args else [],
            "kwargs": kwargs if kwargs else {},
        }
