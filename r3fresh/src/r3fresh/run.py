# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Run context manager for ALM SDK."""
import time
from typing import Dict, Optional

from .events import run_end_event, run_start_event
from .util import create_structured_error, utc_now_iso


class Run:
    """Context manager for agent runs."""

    def __init__(self, alm_instance: "ALM", purpose: Optional[str] = None):  # noqa: F821
        """Initialize a run.

        Args:
            alm_instance: The ALM instance that owns this run
            purpose: Optional purpose description for the run
        """
        self.alm = alm_instance
        self.run_id = None
        self.purpose = purpose
        self._started = False
        self._start_time: Optional[float] = None

        # Statistics tracking
        self._tool_calls_total = 0
        self._tool_calls_allowed = 0
        self._tool_calls_denied = 0
        self._tool_calls_error = 0
        self._tool_calls_retried = 0
        self._tool_latencies: list[float] = []
        self._policy_latencies: list[float] = []
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._handoffs = 0

    def __enter__(self):
        """Enter the run context - emit run.start event."""
        self.run_id = self.alm._new_run_id()
        self._started = True
        self._start_time = time.time()

        event = run_start_event(
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.run_id,
            purpose=self.purpose,
            agent_version=self.alm.agent_version,
            policy_version=self.alm.policy_version,
        )
        self.alm.client.emit(event)

        # Reset policy budget at start of new run
        self.alm.policy.reset_budget()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the run context - emit run.end event with summary."""
        if not self._started:
            return

        success = exc_type is None
        error = None
        if exc_val is not None:
            error = create_structured_error(exc_val, source="agent")

        # Calculate summary statistics
        total_run_duration_ms = (
            (time.time() - self._start_time) * 1000 if self._start_time else 0.0
        )
        avg_tool_latency_ms = (
            sum(self._tool_latencies) / len(self._tool_latencies)
            if self._tool_latencies
            else 0.0
        )
        avg_policy_latency_ms = (
            sum(self._policy_latencies) / len(self._policy_latencies)
            if self._policy_latencies
            else 0.0
        )

        event = run_end_event(
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.run_id,
            success=success,
            error=error,
            agent_version=self.alm.agent_version,
            policy_version=self.alm.policy_version,
            tool_calls_total=self._tool_calls_total,
            tool_calls_allowed=self._tool_calls_allowed,
            tool_calls_denied=self._tool_calls_denied,
            tool_calls_error=self._tool_calls_error,
            tool_calls_retried=self._tool_calls_retried,
            avg_tool_latency_ms=avg_tool_latency_ms,
            avg_policy_latency_ms=avg_policy_latency_ms,
            total_run_duration_ms=total_run_duration_ms,
            tasks_completed=self._tasks_completed,
            tasks_failed=self._tasks_failed,
            handoffs=self._handoffs,
        )
        self.alm.client.emit(event)

        # Flush events at end of run
        self.alm.flush()

        # Return False to not suppress exceptions
        return False

    def record_tool_call(
        self,
        allowed: bool,
        denied: bool,
        error: bool,
        retried: bool,
        tool_latency_ms: float,
        policy_latency_ms: float,
    ) -> None:
        """Record a tool call for statistics."""
        self._tool_calls_total += 1
        if allowed:
            self._tool_calls_allowed += 1
        if denied:
            self._tool_calls_denied += 1
        if error:
            self._tool_calls_error += 1
        if retried:
            self._tool_calls_retried += 1
        if tool_latency_ms > 0:
            self._tool_latencies.append(tool_latency_ms)
        if policy_latency_ms > 0:
            self._policy_latencies.append(policy_latency_ms)

    def record_task_completed(self) -> None:
        """Record a completed task."""
        self._tasks_completed += 1

    def record_task_failed(self) -> None:
        """Record a failed task."""
        self._tasks_failed += 1

    def record_handoff(self) -> None:
        """Record a handoff."""
        self._handoffs += 1
