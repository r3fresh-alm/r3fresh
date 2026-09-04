# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Main ALM class for Agent Lifecycle Management SDK."""
from typing import Any, Callable, ContextManager, Dict, Optional, Set

from .client import EventClient
from .events import (
    evaluation_result_event,
    handoff_event,
    llm_request_event,
    llm_response_event,
    retrieval_request_event,
    retrieval_response_event,
    task_end_event,
    task_start_event,
)
from .policy import Policy
from .run import Run
from .tool import tool
from .telemetry import TelemetryConfig
from .util import new_id, redact_sensitive, utc_now_iso


class ALM:
    """Main ALM (Agent Lifecycle Management) class."""

    def __init__(
        self,
        agent_id: str,
        env: str = "development",
        mode: str = "stdout",
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        allowed_tools: Optional[Set[str]] = None,
        denied_tools: Optional[Set[str]] = None,
        default_allow: bool = True,
        max_tool_calls_per_run: Optional[int] = None,
        agent_version: Optional[str] = None,
        policy_version: Optional[str] = None,
        telemetry: Optional[TelemetryConfig] = None,
    ):
        """Initialize ALM instance.

        Args:
            agent_id: Unique identifier for the agent
            env: Environment name (e.g., "development", "production")
            mode: Event sink mode ("stdout" or "http")
            endpoint: HTTP endpoint URL (required for http mode)
            api_key: API key for HTTP authentication
            allowed_tools: Set of allowed tool names
            denied_tools: Set of denied tool names
            default_allow: Whether to allow tools by default
            max_tool_calls_per_run: Maximum tool calls per run
            agent_version: Optional agent version string
            policy_version: Optional policy version string
        """
        self.agent_id = agent_id
        self.env = env
        self.agent_version = agent_version
        self.policy_version = policy_version
        self.telemetry = telemetry or TelemetryConfig()
        self.client = EventClient(
            mode=mode,
            endpoint=endpoint,
            api_key=api_key,
            event_context=self.telemetry.event_context(),
        )
        self.policy = Policy(
            allowed_tools=allowed_tools,
            denied_tools=denied_tools,
            default_allow=default_allow,
            max_tool_calls_per_run=max_tool_calls_per_run,
        )
        self._current_run: Optional[Run] = None

    def task(
        self,
        task_type: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextManager:
        """Create a task context manager for tracking task outcomes.

        Simple API: automatically tracks task.start/task.end events.

        Args:
            task_type: Optional task type identifier
            description: Optional task description

        Returns:
            Context manager that emits task.start/task.end events
        """
        return TaskContext(
            self, task_type=task_type, description=description,
            metadata=self._safe_metadata(metadata),
        )

    def run(self, purpose: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Run:
        """Create and return a Run context manager.

        Args:
            purpose: Optional purpose description for the run

        Returns:
            Run context manager
        """
        run = Run(alm_instance=self, purpose=purpose, metadata=self._safe_metadata(metadata))
        self._current_run = run
        return run

    def tool(self, tool_name: Optional[str] = None, telemetry: Optional[Dict[str, Any]] = None):
        """Return a decorator for wrapping tool functions.

        Args:
            tool_name: Optional name for the tool

        Returns:
            Decorator function
        """
        return tool(self, tool_name=tool_name, telemetry=self._safe_metadata(telemetry))

    def flush(self) -> None:
        """Flush queued events."""
        self.client.flush()

    def _new_run_id(self) -> str:
        """Generate a new run ID."""
        return new_id()

    def _current_run_id(self) -> Optional[str]:
        """Get the current run ID if a run is active."""
        if self._current_run and self._current_run.run_id:
            return self._current_run.run_id
        return None

    def handoff(
        self,
        to_agent_id: str,
        reason: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a handoff event.

        Simple API for agent-to-agent handoffs.

        Args:
            to_agent_id: Target agent ID for the handoff
            reason: Optional reason for handoff
            context: Optional context dictionary to pass
        """
        if self._current_run:
            self._current_run.record_handoff()

        event = handoff_event(
            event_id=new_id(),
            timestamp=utc_now_iso(),
            agent_id=self.agent_id,
            env=self.env,
            run_id=self._current_run_id(),
            from_agent_id=self.agent_id,
            to_agent_id=to_agent_id,
            reason=reason,
            context=self._safe_payload(context, self.telemetry.capture_inputs),
            custom_metadata=self._safe_metadata(metadata),
            agent_version=self.agent_version,
            policy_version=self.policy_version,
        )
        self.client.emit(event)

    def llm_request(self, provider: Optional[str] = None, model: Optional[str] = None,
                    streaming: Optional[bool] = None, temperature: Optional[float] = None,
                    max_tokens: Optional[int] = None, prompt: Optional[Any] = None,
                    attempt: int = 1, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit manual LLM request telemetry without requiring a provider adapter."""
        self.client.emit(llm_request_event(
            event_id=new_id(), timestamp=utc_now_iso(), agent_id=self.agent_id, env=self.env,
            run_id=self._current_run_id(), provider=provider, model=model, streaming=streaming,
            temperature=temperature, max_tokens=max_tokens, attempt=attempt,
            prompt=self._safe_payload(prompt, self.telemetry.capture_prompts),
            custom_metadata=self._safe_metadata(metadata), agent_version=self.agent_version,
            policy_version=self.policy_version,
        ))

    def llm_response(self, provider: Optional[str] = None, model: Optional[str] = None,
                     input_tokens: Optional[int] = None, output_tokens: Optional[int] = None,
                     total_tokens: Optional[int] = None, context_tokens: Optional[int] = None,
                     context_window_size: Optional[int] = None,
                     time_to_first_token_ms: Optional[float] = None,
                     generation_latency_ms: Optional[float] = None,
                     total_latency_ms: Optional[float] = None,
                     estimated_cost_usd: Optional[float] = None, streaming: Optional[bool] = None,
                     temperature: Optional[float] = None, max_tokens: Optional[int] = None,
                     finish_reason: Optional[str] = None, attempt: int = 1, retries: int = 0,
                     error: Optional[Dict[str, Any]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit manual LLM response telemetry and update the active run summary."""
        if self._current_run:
            self._current_run.record_llm_call(input_tokens, output_tokens, total_tokens, estimated_cost_usd, retries)
        self.client.emit(llm_response_event(
            event_id=new_id(), timestamp=utc_now_iso(), agent_id=self.agent_id, env=self.env,
            run_id=self._current_run_id(), provider=provider, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
            context_tokens=context_tokens, context_window_size=context_window_size,
            time_to_first_token_ms=time_to_first_token_ms,
            generation_latency_ms=generation_latency_ms, total_latency_ms=total_latency_ms,
            estimated_cost_usd=estimated_cost_usd, streaming=streaming, temperature=temperature,
            max_tokens=max_tokens, finish_reason=finish_reason, attempt=attempt, retries=retries,
            error=self._safe_metadata(error), custom_metadata=self._safe_metadata(metadata),
            agent_version=self.agent_version, policy_version=self.policy_version,
        ))

    def retrieval_request(self, retriever_name: Optional[str] = None,
                          vector_store: Optional[str] = None, top_k: Optional[int] = None,
                          filters: Optional[Dict[str, Any]] = None, query: Optional[Any] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit manual retrieval request telemetry without document contents."""
        self.client.emit(retrieval_request_event(
            event_id=new_id(), timestamp=utc_now_iso(), agent_id=self.agent_id, env=self.env,
            run_id=self._current_run_id(), retriever_name=retriever_name, vector_store=vector_store,
            top_k=top_k, filters=self._safe_metadata(filters),
            query=self._safe_payload(query, self.telemetry.capture_inputs),
            custom_metadata=self._safe_metadata(metadata), agent_version=self.agent_version,
            policy_version=self.policy_version,
        ))

    def retrieval_response(self, metadata: Optional[Dict[str, Any]] = None, **metrics: Any) -> None:
        """Emit aggregate retrieval response telemetry; documents are never included."""
        if self._current_run:
            self._current_run.record_retrieval_call()
        self.client.emit(retrieval_response_event(
            event_id=new_id(), timestamp=utc_now_iso(), agent_id=self.agent_id, env=self.env,
            run_id=self._current_run_id(), custom_metadata=self._safe_metadata(metadata),
            agent_version=self.agent_version, policy_version=self.policy_version, **metrics,
        ))

    def evaluation_result(self, metadata: Optional[Dict[str, Any]] = None, **result: Any) -> None:
        """Emit a generic deterministic, model, or human evaluation result."""
        if "feedback" in result:
            result["feedback"] = self._safe_payload(result["feedback"], self.telemetry.capture_outputs)
        self.client.emit(evaluation_result_event(
            event_id=new_id(), timestamp=utc_now_iso(), agent_id=self.agent_id, env=self.env,
            run_id=self._current_run_id(), custom_metadata=self._safe_metadata(metadata),
            agent_version=self.agent_version, policy_version=self.policy_version, **result,
        ))

    def _safe_metadata(self, metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if metadata is None:
            return None
        return redact_sensitive(metadata) if self.telemetry.redact_sensitive_data else metadata

    def _safe_payload(self, payload: Optional[Any], enabled: bool) -> Optional[Any]:
        if not enabled or payload is None:
            return None
        return redact_sensitive(payload) if self.telemetry.redact_sensitive_data else payload

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush and close."""
        self.flush()
        self.client.close()


class TaskContext:
    """Context manager for tracking tasks."""

    def __init__(
        self,
        alm_instance: ALM,
        task_type: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize task context.

        Args:
            alm_instance: The ALM instance
            task_type: Optional task type
            description: Optional task description
        """
        self.alm = alm_instance
        self.metadata = metadata or {}
        self.task_type = task_type
        self.description = description
        self.task_id = None

    def __enter__(self):
        """Enter task context - emit task.start."""
        self.task_id = new_id()

        event = task_start_event(
            event_id=new_id(),
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.alm._current_run_id(),
            task_id=self.task_id,
            task_type=self.task_type,
            description=self.description,
            custom_metadata=self.metadata,
            agent_version=self.alm.agent_version,
            policy_version=self.alm.policy_version,
        )
        self.alm.client.emit(event)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit task context - emit task.end."""
        success = exc_type is None
        error = None

        if exc_val is not None:
            from .util import create_structured_error

            error = create_structured_error(exc_val, source="agent")

        event = task_end_event(
            event_id=new_id(),
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.alm._current_run_id(),
            task_id=self.task_id,
            success=success,
            error=error,
            custom_metadata=self.metadata,
            agent_version=self.alm.agent_version,
            policy_version=self.alm.policy_version,
        )
        self.alm.client.emit(event)

        # Update run statistics
        if self.alm._current_run:
            if success:
                self.alm._current_run.record_task_completed()
            else:
                self.alm._current_run.record_task_failed()

        return False  # Don't suppress exceptions
