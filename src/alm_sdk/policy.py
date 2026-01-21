# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Policy enforcement for ALM SDK."""
from typing import Optional, Set


class Policy:
    """Policy class for tool allow/deny decisions."""

    def __init__(
        self,
        allowed_tools: Optional[Set[str]] = None,
        denied_tools: Optional[Set[str]] = None,
        default_allow: bool = True,
        max_tool_calls_per_run: Optional[int] = None,
    ):
        """Initialize policy.

        Args:
            allowed_tools: Set of allowed tool names (None means no restriction)
            denied_tools: Set of denied tool names
            default_allow: Whether to allow by default if not in allow/deny lists
            max_tool_calls_per_run: Maximum tool calls per run (None = unlimited)
        """
        self.allowed_tools = allowed_tools or set()
        self.denied_tools = denied_tools or set()
        self.default_allow = default_allow
        self.max_tool_calls_per_run = max_tool_calls_per_run
        self._tool_call_count = 0

    def check_tool(self, tool_name: str) -> tuple[bool, str]:
        """Check if a tool is allowed.

        Args:
            tool_name: Name of the tool to check

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Check budget
        if self.max_tool_calls_per_run is not None:
            if self._tool_call_count >= self.max_tool_calls_per_run:
                return False, f"Budget exceeded: {self._tool_call_count}/{self.max_tool_calls_per_run} tool calls"

        # Check explicit deny list
        if tool_name in self.denied_tools:
            return False, f"Tool '{tool_name}' is in denied_tools list"

        # Check explicit allow list
        if self.allowed_tools:
            if tool_name not in self.allowed_tools:
                return False, f"Tool '{tool_name}' is not in allowed_tools list"

        # Default allow/deny
        if not self.default_allow and not self.allowed_tools:
            return False, "default_allow is False and no allowed_tools specified"

        return True, "allowed"

    def record_tool_call(self) -> None:
        """Record that a tool was called (for budget tracking)."""
        self._tool_call_count += 1

    def reset_budget(self) -> None:
        """Reset the tool call counter (call at start of new run)."""
        self._tool_call_count = 0
