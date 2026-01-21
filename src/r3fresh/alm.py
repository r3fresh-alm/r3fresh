# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Main ALM class for Agent Lifecycle Management SDK."""
from typing import Any, Callable, ContextManager, Dict, Optional, Set

from .client import EventClient
from .events import handoff_event, task_end_event, task_start_event
from .policy import Policy
from .run import Run
from .tool import tool
from .util import new_id, utc_now_iso


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
        self.client = EventClient(mode=mode, endpoint=endpoint, api_key=api_key)
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
    ) -> ContextManager:
        """Create a task context manager for tracking task outcomes.

        Simple API: automatically tracks task.start/task.end events.

        Args:
            task_type: Optional task type identifier
            description: Optional task description

        Returns:
            Context manager that emits task.start/task.end events
        """
        return TaskContext(self, task_type=task_type, description=description)

    def run(self, purpose: Optional[str] = None) -> Run:
        """Create and return a Run context manager.

        Args:
            purpose: Optional purpose description for the run

        Returns:
            Run context manager
        """
        run = Run(alm_instance=self, purpose=purpose)
        self._current_run = run
        return run

    def tool(self, tool_name: Optional[str] = None):
        """Return a decorator for wrapping tool functions.

        Args:
            tool_name: Optional name for the tool

        Returns:
            Decorator function
        """
        return tool(self, tool_name=tool_name)

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
            timestamp=utc_now_iso(),
            agent_id=self.agent_id,
            env=self.env,
            run_id=self._current_run_id(),
            from_agent_id=self.agent_id,
            to_agent_id=to_agent_id,
            reason=reason,
            context=context,
            agent_version=self.agent_version,
            policy_version=self.policy_version,
        )
        self.client.emit(event)

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
    ):
        """Initialize task context.

        Args:
            alm_instance: The ALM instance
            task_type: Optional task type
            description: Optional task description
        """
        self.alm = alm_instance
        self.task_type = task_type
        self.description = description
        self.task_id = None

    def __enter__(self):
        """Enter task context - emit task.start."""
        self.task_id = new_id()

        event = task_start_event(
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.alm._current_run_id(),
            task_id=self.task_id,
            task_type=self.task_type,
            description=self.description,
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
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.alm._current_run_id(),
            task_id=self.task_id,
            success=success,
            error=error,
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
