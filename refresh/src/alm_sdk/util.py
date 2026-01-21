# SPDX-FileCopyrightText: 2026-present zengjosh <zeng080407@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Utility functions for ALM SDK."""
import re
import traceback
from datetime import datetime, timezone
from typing import Any, Dict
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
