# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Run context manager for ALM SDK."""
import time
from typing import Any, Dict, Optional

from .events import run_end_event, run_start_event
from .util import create_structured_error, new_id, utc_now_iso


class Run:
    """Context manager for agent runs."""

    def __init__(
        self, alm_instance: "ALM", purpose: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):  # noqa: F821
        """Initialize a run.

        Args:
            alm_instance: The ALM instance that owns this run
            purpose: Optional purpose description for the run
        """
        self.alm = alm_instance
        self.run_id = None
        self.purpose = purpose
        self.metadata = metadata or {}
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
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_tokens = 0
        self._total_estimated_cost_usd = 0.0
        self._total_llm_calls = 0
        self._total_retrieval_calls = 0
        self._retries = 0

    def __enter__(self):
        """Enter the run context - emit run.start event."""
        self.run_id = self.alm._new_run_id()
        self._started = True
        self._start_time = time.time()

        event = run_start_event(
            event_id=new_id(),
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.run_id,
            purpose=self.purpose,
            custom_metadata=self.metadata,
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
            event_id=new_id(),
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
            total_input_tokens=self._total_input_tokens,
            total_output_tokens=self._total_output_tokens,
            total_tokens=self._total_tokens,
            total_estimated_cost_usd=self._total_estimated_cost_usd,
            total_llm_calls=self._total_llm_calls,
            total_retrieval_calls=self._total_retrieval_calls,
            retries=self._retries,
            custom_metadata=self.metadata,
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

    def record_llm_call(
        self, input_tokens: Optional[int], output_tokens: Optional[int],
        total_tokens: Optional[int], estimated_cost_usd: Optional[float], retries: int,
    ) -> None:
        """Accumulate optional LLM usage for the enclosing run."""
        self._total_llm_calls += 1
        self._total_input_tokens += input_tokens or 0
        self._total_output_tokens += output_tokens or 0
        self._total_tokens += total_tokens if total_tokens is not None else (input_tokens or 0) + (output_tokens or 0)
        self._total_estimated_cost_usd += estimated_cost_usd or 0.0
        self._retries += retries

    def record_retrieval_call(self) -> None:
        """Accumulate a retrieval operation for the enclosing run."""
        self._total_retrieval_calls += 1
