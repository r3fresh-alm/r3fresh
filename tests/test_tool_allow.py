"""Test tool allow behavior."""
import json
import sys
from io import StringIO

from r3fresh import ALM


def test_tool_allow():
    """Test that policy allows tool, tool executes, events include request and response."""
    # Capture stdout
    captured_output = StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured_output

    try:
        alm = ALM(
            agent_id="test-agent",
            env="test",
            mode="stdout",
            allowed_tools={"add_numbers"},
        )

        @alm.tool("add_numbers")
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        with alm.run(purpose="Test tool allow"):
            result = add_numbers(2, 3)

        assert result == 5

        # Flush to ensure all events are captured
        alm.flush()

        # Parse stdout output
        output = captured_output.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        # Check that we have events
        assert len(lines) > 0

        # Parse events
        events = [json.loads(line) for line in lines]

        # Find run.start event
        run_start = next((e for e in events if e["event_type"] == "run.start"), None)
        assert run_start is not None

        # Find tool.request event
        tool_request = next((e for e in events if e["event_type"] == "tool.request"), None)
        assert tool_request is not None
        assert tool_request["metadata"]["tool_name"] == "add_numbers"
        assert "tool_call_id" in tool_request["metadata"]
        tool_call_id = tool_request["metadata"]["tool_call_id"]

        # Find policy.decision event (allow)
        policy_decision = next(
            (e for e in events if e["event_type"] == "policy.decision" and e["metadata"]["decision"] == "allow"),
            None,
        )
        assert policy_decision is not None
        assert policy_decision["metadata"]["tool_call_id"] == tool_call_id
        assert "latency_ms" in policy_decision["metadata"]

        # Find tool.response event
        tool_response = next((e for e in events if e["event_type"] == "tool.response"), None)
        assert tool_response is not None
        assert tool_response["metadata"]["status"] == "success"
        assert tool_response["metadata"]["tool_name"] == "add_numbers"
        assert tool_response["metadata"]["tool_call_id"] == tool_call_id
        assert "policy_latency_ms" in tool_response["metadata"]
        assert "tool_latency_ms" in tool_response["metadata"]
        assert "total_latency_ms" in tool_response["metadata"]

        # Find run.end event
        run_end = next((e for e in events if e["event_type"] == "run.end"), None)
        assert run_end is not None
        assert run_end["metadata"]["success"] is True

    finally:
        sys.stdout = original_stdout
