"""Test tool deny behavior."""
import json
import sys
from io import StringIO

import pytest

from r3fresh import ALM


def test_tool_deny():
    """Test that policy denies tool, tool does not execute, raises PermissionError, emits deny event."""
    # Capture stdout
    captured_output = StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured_output

    try:
        alm = ALM(
            agent_id="test-agent",
            env="test",
            mode="stdout",
            denied_tools={"blocked_tool"},
        )

        execution_flag = False

        @alm.tool("blocked_tool")
        def blocked_tool() -> str:
            """A blocked tool that should not execute."""
            nonlocal execution_flag
            execution_flag = True
            return "should not execute"

        with alm.run(purpose="Test tool deny"):
            # Tool should raise PermissionError
            with pytest.raises(PermissionError, match="Tool 'blocked_tool' denied"):
                blocked_tool()

        # Verify tool did not execute
        assert execution_flag is False

        # Flush to ensure all events are captured
        alm.flush()

        # Parse stdout output
        output = captured_output.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        # Check that we have events
        assert len(lines) > 0

        # Parse events
        events = [json.loads(line) for line in lines]

        # Find tool.request event
        tool_request = next((e for e in events if e["event_type"] == "tool.request"), None)
        assert tool_request is not None
        assert tool_request["metadata"]["tool_name"] == "blocked_tool"
        assert "tool_call_id" in tool_request["metadata"]
        tool_call_id = tool_request["metadata"]["tool_call_id"]

        # Find policy.decision event (deny)
        policy_decision = next(
            (e for e in events if e["event_type"] == "policy.decision" and e["metadata"]["decision"] == "deny"),
            None,
        )
        assert policy_decision is not None
        assert policy_decision["metadata"]["tool_name"] == "blocked_tool"
        assert policy_decision["metadata"]["tool_call_id"] == tool_call_id
        assert "latency_ms" in policy_decision["metadata"]

        # Should have a tool.response event with status="denied"
        tool_response = next((e for e in events if e["event_type"] == "tool.response"), None)
        assert tool_response is not None
        assert tool_response["metadata"]["tool_name"] == "blocked_tool"
        assert tool_response["metadata"]["status"] == "denied"
        assert tool_response["metadata"]["tool_call_id"] == tool_call_id
        assert "error" in tool_response["metadata"]
        assert "policy_latency_ms" in tool_response["metadata"]
        assert "tool_latency_ms" in tool_response["metadata"]
        assert tool_response["metadata"]["tool_latency_ms"] == 0.0  # Tool didn't execute
        assert "total_latency_ms" in tool_response["metadata"]

        # Find run.end event (should still be successful since we caught the exception)
        run_end = next((e for e in events if e["event_type"] == "run.end"), None)
        assert run_end is not None
        # Note: run.end will be successful=True because we caught the exception in the test

    finally:
        sys.stdout = original_stdout
