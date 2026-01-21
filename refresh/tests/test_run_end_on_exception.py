"""Test run.end event on exception."""
import json
import sys
from io import StringIO

from alm_sdk import ALM


def test_run_end_on_exception():
    """Test that inside run, raising exception emits run.end with failure."""
    # Capture stdout
    captured_output = StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured_output

    try:
        alm = ALM(
            agent_id="test-agent",
            env="test",
            mode="stdout",
        )

        with alm.run(purpose="Test exception handling"):
            # Raise an exception inside the run
            raise ValueError("Test exception")

    except ValueError:
        # Expected exception
        pass
    finally:
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

        # Find run.end event
        run_end = next((e for e in events if e["event_type"] == "run.end"), None)
        assert run_end is not None
        assert run_end["metadata"]["success"] is False
        assert "error" in run_end["metadata"]
        assert "ValueError" in run_end["metadata"]["error"]

        sys.stdout = original_stdout
