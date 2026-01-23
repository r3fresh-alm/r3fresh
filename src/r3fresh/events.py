# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Event objects for ALM SDK."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .__about__ import __version__ as SDK_VERSION

# Schema version - increment when event structure changes
SCHEMA_VERSION = "1.0"


class Event(BaseModel):
    """Base event with common fields."""

    event_id: str = Field(..., description="Unique event ID (UUID) for idempotency and deduplication")
    timestamp: str = Field(..., description="RFC3339 timestamp")
    event_type: str = Field(..., description="Type of event")
    agent_id: str = Field(..., description="Agent identifier")
    env: str = Field(..., description="Environment name")
    run_id: Optional[str] = Field(None, description="Run identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    # Version tracking fields
    schema_version: str = Field(default=SCHEMA_VERSION, description="Event schema version")
    sdk_version: str = Field(default=SDK_VERSION, description="SDK version")
    agent_version: Optional[str] = Field(None, description="Agent version")
    policy_version: Optional[str] = Field(None, description="Policy version")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2026-01-01T00:00:00.000Z",
                "event_type": "run.start",
                "agent_id": "agent-123",
                "env": "production",
                "run_id": "run-456",
                "metadata": {},
            }
        }


def run_start_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: str,
    purpose: Optional[str] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a run.start event."""
    metadata: Dict[str, Any] = {}
    if purpose:
        metadata["purpose"] = purpose
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="run.start",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def run_end_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: str,
    success: bool,
    error: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
    # Summary fields
    tool_calls_total: int = 0,
    tool_calls_allowed: int = 0,
    tool_calls_denied: int = 0,
    tool_calls_error: int = 0,
    tool_calls_retried: int = 0,
    avg_tool_latency_ms: float = 0.0,
    avg_policy_latency_ms: float = 0.0,
    total_run_duration_ms: float = 0.0,
    tasks_completed: int = 0,
    tasks_failed: int = 0,
    handoffs: int = 0,
) -> Event:
    """Create a run.end event with summary statistics."""
    metadata: Dict[str, Any] = {
        "success": success,
        "summary": {
            "tool_calls": {
                "total": tool_calls_total,
                "allowed": tool_calls_allowed,
                "denied": tool_calls_denied,
                "error": tool_calls_error,
                "retried": tool_calls_retried,
            },
            "latencies": {
                "avg_tool_ms": avg_tool_latency_ms,
                "avg_policy_ms": avg_policy_latency_ms,
                "total_run_ms": total_run_duration_ms,
            },
            "tasks": {
                "completed": tasks_completed,
                "failed": tasks_failed,
            },
            "handoffs": handoffs,
        },
    }
    if error:
        metadata["error"] = error
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="run.end",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def tool_request_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    tool_call_id: str,
    args: Dict[str, Any],
    attempt: int = 1,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a tool.request event."""
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="tool.request",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata={
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "args": args,
            "attempt": attempt,
        },
        agent_version=agent_version,
        policy_version=policy_version,
    )


def tool_response_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    tool_call_id: str,
    status: str,
    policy_latency_ms: float,
    tool_latency_ms: float,
    total_latency_ms: float,
    attempt: int = 1,
    retries: int = 0,
    error: Optional[Dict[str, Any]] = None,
    result: Optional[Any] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a tool.response event."""
    metadata: Dict[str, Any] = {
        "tool_name": tool_name,
        "tool_call_id": tool_call_id,
        "status": status,
        "policy_latency_ms": policy_latency_ms,
        "tool_latency_ms": tool_latency_ms,
        "total_latency_ms": total_latency_ms,
        "attempt": attempt,
        "retries": retries,
    }
    if error:
        metadata["error"] = error
    if result is not None:
        metadata["result"] = result
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="tool.response",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def policy_decision_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    tool_call_id: str,
    decision: str,
    reason: str,
    latency_ms: float,
    attempt: int = 1,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a policy.decision event."""
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="policy.decision",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata={
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "decision": decision,
            "reason": reason,
            "latency_ms": latency_ms,
            "attempt": attempt,
        },
        agent_version=agent_version,
        policy_version=policy_version,
    )


def task_start_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    task_id: str,
    task_type: Optional[str] = None,
    description: Optional[str] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a task.start event."""
    metadata: Dict[str, Any] = {"task_id": task_id}
    if task_type:
        metadata["task_type"] = task_type
    if description:
        metadata["description"] = description
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="task.start",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def task_end_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    task_id: str,
    success: bool,
    error: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a task.end event."""
    metadata: Dict[str, Any] = {
        "task_id": task_id,
        "success": success,
    }
    if error:
        metadata["error"] = error
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="task.end",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def handoff_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    from_agent_id: str,
    to_agent_id: str,
    reason: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a handoff event."""
    metadata: Dict[str, Any] = {
        "from_agent_id": from_agent_id,
        "to_agent_id": to_agent_id,
    }
    if reason:
        metadata["reason"] = reason
    if context:
        metadata["context"] = context
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="handoff",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )
