# SPDX-FileCopyrightText: 2026-present zengjosh <zeng080407@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Event objects for ALM SDK."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Base event with common fields."""

    timestamp: str = Field(..., description="ISO timestamp")
    event_type: str = Field(..., description="Type of event")
    agent_id: str = Field(..., description="Agent identifier")
    env: str = Field(..., description="Environment name")
    run_id: Optional[str] = Field(None, description="Run identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-01T00:00:00Z",
                "event_type": "run.start",
                "agent_id": "agent-123",
                "env": "production",
                "run_id": "run-456",
                "metadata": {},
            }
        }


def run_start_event(
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: str,
    purpose: Optional[str] = None,
) -> Event:
    """Create a run.start event."""
    metadata: Dict[str, Any] = {}
    if purpose:
        metadata["purpose"] = purpose
    return Event(
        timestamp=timestamp,
        event_type="run.start",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
    )


def run_end_event(
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: str,
    success: bool,
    error: Optional[str] = None,
) -> Event:
    """Create a run.end event."""
    metadata: Dict[str, Any] = {"success": success}
    if error:
        metadata["error"] = error
    return Event(
        timestamp=timestamp,
        event_type="run.end",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
    )


def tool_request_event(
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    args: Dict[str, Any],
) -> Event:
    """Create a tool.request event."""
    return Event(
        timestamp=timestamp,
        event_type="tool.request",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata={"tool_name": tool_name, "args": args},
    )


def tool_response_event(
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    status: str,
    latency_ms: float,
    error: Optional[str] = None,
    result: Optional[Any] = None,
) -> Event:
    """Create a tool.response event."""
    metadata: Dict[str, Any] = {
        "tool_name": tool_name,
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        metadata["error"] = error
    if result is not None:
        metadata["result"] = result
    return Event(
        timestamp=timestamp,
        event_type="tool.response",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
    )


def policy_decision_event(
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    decision: str,
    reason: str,
) -> Event:
    """Create a policy.decision event."""
    return Event(
        timestamp=timestamp,
        event_type="policy.decision",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata={
            "tool_name": tool_name,
            "decision": decision,
            "reason": reason,
        },
    )
