# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Tool decorator for ALM SDK."""
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from .events import policy_decision_event, tool_request_event, tool_response_event
from .util import (
    create_structured_error,
    new_id,
    normalize_args,
    redact_sensitive,
    utc_now_iso,
)


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
            # Generate tool_call_id for correlation across events
            tool_call_id = new_id()

            # Track attempts and retries
            attempt = 1
            max_retries = 0  # Could be made configurable in the future
            retries = 0

            while True:
                # Capture start time at the very beginning for accurate latency
                total_start_time = time.time()

                # Normalize args to named parameters for better analytics
                normalized_args = normalize_args(func, args, kwargs)
                # Redact sensitive info from normalized args
                redacted_args = redact_sensitive(normalized_args)

                # Emit tool.request
                request_event = tool_request_event(
                    event_id=new_id(),
                    timestamp=utc_now_iso(),
                    agent_id=alm_instance.agent_id,
                    env=alm_instance.env,
                    run_id=alm_instance._current_run_id(),
                    tool_name=name,
                    tool_call_id=tool_call_id,
                    args=redacted_args,
                    attempt=attempt,
                    agent_version=alm_instance.agent_version,
                    policy_version=alm_instance.policy_version,
                )
                alm_instance.client.emit(request_event)

                # Check policy and measure policy latency
                policy_start_time = time.time()
                allowed, reason = alm_instance.policy.check_tool(name)
                policy_latency_ms = (time.time() - policy_start_time) * 1000

                if not allowed:
                    # Emit policy.decision deny
                    decision_event = policy_decision_event(
                        event_id=new_id(),
                        timestamp=utc_now_iso(),
                        agent_id=alm_instance.agent_id,
                        env=alm_instance.env,
                        run_id=alm_instance._current_run_id(),
                        tool_name=name,
                        tool_call_id=tool_call_id,
                        decision="deny",
                        reason=reason,
                        latency_ms=policy_latency_ms,
                        attempt=attempt,
                        agent_version=alm_instance.agent_version,
                        policy_version=alm_instance.policy_version,
                    )
                    alm_instance.client.emit(decision_event)

                    # Emit tool.response with status="denied" before raising
                    total_latency_ms = (time.time() - total_start_time) * 1000
                    denied_error = create_structured_error(
                        PermissionError(f"Tool '{name}' denied: {reason}"),
                        source="policy",
                    )
                    denied_response_event = tool_response_event(
                        event_id=new_id(),
                        timestamp=utc_now_iso(),
                        agent_id=alm_instance.agent_id,
                        env=alm_instance.env,
                        run_id=alm_instance._current_run_id(),
                        tool_name=name,
                        tool_call_id=tool_call_id,
                        status="denied",
                        policy_latency_ms=policy_latency_ms,
                        tool_latency_ms=0.0,  # Tool didn't execute
                        total_latency_ms=total_latency_ms,
                        attempt=attempt,
                        retries=retries,
                        error=denied_error,
                        result=None,
                        agent_version=alm_instance.agent_version,
                        policy_version=alm_instance.policy_version,
                    )
                    alm_instance.client.emit(denied_response_event)

                    # Record statistics
                    if alm_instance._current_run:
                        alm_instance._current_run.record_tool_call(
                            allowed=False,
                            denied=True,
                            error=False,
                            retried=retries > 0,
                            tool_latency_ms=0.0,
                            policy_latency_ms=policy_latency_ms,
                        )

                    raise PermissionError(f"Tool '{name}' denied: {reason}")

                # Emit policy.decision allow
                decision_event = policy_decision_event(
                    event_id=new_id(),
                    timestamp=utc_now_iso(),
                    agent_id=alm_instance.agent_id,
                    env=alm_instance.env,
                    run_id=alm_instance._current_run_id(),
                    tool_name=name,
                    tool_call_id=tool_call_id,
                    decision="allow",
                    reason=reason,
                    latency_ms=policy_latency_ms,
                    attempt=attempt,
                    agent_version=alm_instance.agent_version,
                    policy_version=alm_instance.policy_version,
                )
                alm_instance.client.emit(decision_event)

                # Execute tool and time it
                tool_start_time = time.time()
                status = "success"
                error = None
                result = None

                try:
                    result = func(*args, **kwargs)
                    # Record successful tool call for budget
                    alm_instance.policy.record_tool_call()

                    # Emit successful tool.response
                    tool_latency_ms = (time.time() - tool_start_time) * 1000
                    total_latency_ms = (time.time() - total_start_time) * 1000

                    response_event = tool_response_event(
                        event_id=new_id(),
                        timestamp=utc_now_iso(),
                        agent_id=alm_instance.agent_id,
                        env=alm_instance.env,
                        run_id=alm_instance._current_run_id(),
                        tool_name=name,
                        tool_call_id=tool_call_id,
                        status=status,
                        policy_latency_ms=policy_latency_ms,
                        tool_latency_ms=tool_latency_ms,
                        total_latency_ms=total_latency_ms,
                        attempt=attempt,
                        retries=retries,
                        error=error,
                        result=redact_sensitive(result) if result is not None else None,
                        agent_version=alm_instance.agent_version,
                        policy_version=alm_instance.policy_version,
                    )
                    alm_instance.client.emit(response_event)

                    # Record statistics
                    if alm_instance._current_run:
                        alm_instance._current_run.record_tool_call(
                            allowed=True,
                            denied=False,
                            error=False,
                            retried=retries > 0,
                            tool_latency_ms=tool_latency_ms,
                            policy_latency_ms=policy_latency_ms,
                        )

                    return result

                except Exception as e:
                    tool_latency_ms = (time.time() - tool_start_time) * 1000
                    total_latency_ms = (time.time() - total_start_time) * 1000

                    # Create structured error
                    error = create_structured_error(e, source="tool")

                    # Check if we should retry (retryable error and attempts left)
                    should_retry = (
                        error.get("retryable", False)
                        and attempt <= max_retries
                        and attempt < 3
                    )  # Cap at 3 attempts

                    if should_retry:
                        # Retry - increment attempt and retry count
                        attempt += 1
                        retries += 1
                        # Record failed attempt
                        if alm_instance._current_run:
                            alm_instance._current_run.record_tool_call(
                                allowed=True,
                                denied=False,
                                error=True,
                                retried=True,
                                tool_latency_ms=tool_latency_ms,
                                policy_latency_ms=policy_latency_ms,
                            )
                        # Continue loop to retry
                        continue

                    # No retry or max retries reached - emit error response
                    status = "error"
                    response_event = tool_response_event(
                        event_id=new_id(),
                        timestamp=utc_now_iso(),
                        agent_id=alm_instance.agent_id,
                        env=alm_instance.env,
                        run_id=alm_instance._current_run_id(),
                        tool_name=name,
                        tool_call_id=tool_call_id,
                        status=status,
                        policy_latency_ms=policy_latency_ms,
                        tool_latency_ms=tool_latency_ms,
                        total_latency_ms=total_latency_ms,
                        attempt=attempt,
                        retries=retries,
                        error=error,
                        result=None,
                        agent_version=alm_instance.agent_version,
                        policy_version=alm_instance.policy_version,
                    )
                    alm_instance.client.emit(response_event)

                    # Record statistics
                    if alm_instance._current_run:
                        alm_instance._current_run.record_tool_call(
                            allowed=True,
                            denied=False,
                            error=True,
                            retried=retries > 0,
                            tool_latency_ms=tool_latency_ms,
                            policy_latency_ms=policy_latency_ms,
                        )

                    # Still record tool call for budget purposes
                    alm_instance.policy.record_tool_call()
                    raise

        return wrapper

    return decorator
