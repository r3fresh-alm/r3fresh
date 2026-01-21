# SPDX-FileCopyrightText: 2026-present zengjosh <zeng080407@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Main ALM class for Agent Lifecycle Management SDK."""
from typing import Optional, Set

from .client import EventClient
from .policy import Policy
from .run import Run
from .tool import tool
from .util import new_id


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
        """
        self.agent_id = agent_id
        self.env = env
        self.client = EventClient(mode=mode, endpoint=endpoint, api_key=api_key)
        self.policy = Policy(
            allowed_tools=allowed_tools,
            denied_tools=denied_tools,
            default_allow=default_allow,
            max_tool_calls_per_run=max_tool_calls_per_run,
        )
        self._current_run: Optional[Run] = None

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

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush and close."""
        self.flush()
        self.client.close()
