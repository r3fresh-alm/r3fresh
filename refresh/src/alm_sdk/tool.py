# SPDX-FileCopyrightText: 2026-present zengjosh <zeng080407@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Tool decorator for ALM SDK."""
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from .events import policy_decision_event, tool_request_event, tool_response_event
from .util import redact_sensitive, safe_error, utc_now_iso


def tool(
    alm_instance: "ALM",  # noqa: F821
    tool_name: Optional[str] = None,
) -> Callable:
    """Decorator factory for wrapping tool functions.

    Args:
        alm_instance: The ALM instance
        tool_name: Optional name for the tool (defaults to function name)

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        name = tool_name or func.__name__

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Redact sensitive info from args/kwargs
            redacted_kwargs = redact_sensitive(kwargs) if kwargs else {}
            redacted_args = redact_sensitive(args) if args else []

            # Emit tool.request
            request_event = tool_request_event(
                timestamp=utc_now_iso(),
                agent_id=alm_instance.agent_id,
                env=alm_instance.env,
                run_id=alm_instance._current_run_id(),
                tool_name=name,
                args={"args": redacted_args, "kwargs": redacted_kwargs},
            )
            alm_instance.client.emit(request_event)

            # Check policy
            allowed, reason = alm_instance.policy.check_tool(name)
            if not allowed:
                # Emit policy.decision deny
                decision_event = policy_decision_event(
                    timestamp=utc_now_iso(),
                    agent_id=alm_instance.agent_id,
                    env=alm_instance.env,
                    run_id=alm_instance._current_run_id(),
                    tool_name=name,
                    decision="deny",
                    reason=reason,
                )
                alm_instance.client.emit(decision_event)
                raise PermissionError(f"Tool '{name}' denied: {reason}")

            # Emit policy.decision allow
            decision_event = policy_decision_event(
                timestamp=utc_now_iso(),
                agent_id=alm_instance.agent_id,
                env=alm_instance.env,
                run_id=alm_instance._current_run_id(),
                tool_name=name,
                decision="allow",
                reason=reason,
            )
            alm_instance.client.emit(decision_event)

            # Execute tool and time it
            start_time = time.time()
            status = "success"
            error = None
            result = None

            try:
                result = func(*args, **kwargs)
                # Record successful tool call for budget
                alm_instance.policy.record_tool_call()
            except Exception as e:
                status = "error"
                error_dict = safe_error(e)
                error = f"{error_dict['type']}: {error_dict['message']}"
                # Still record tool call for budget purposes
                alm_instance.policy.record_tool_call()
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000

                # Emit tool.response
                response_event = tool_response_event(
                    timestamp=utc_now_iso(),
                    agent_id=alm_instance.agent_id,
                    env=alm_instance.env,
                    run_id=alm_instance._current_run_id(),
                    tool_name=name,
                    status=status,
                    latency_ms=latency_ms,
                    error=error,
                    result=redact_sensitive(result) if result is not None else None,
                )
                alm_instance.client.emit(response_event)

            return result

        return wrapper

    return decorator
