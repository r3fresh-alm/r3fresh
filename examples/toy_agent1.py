"""
Toy agent exercising most ALM SDK features.

What this tests (stdout mode):
- run.start / run.end (with summary)
- tool.request / policy.decision / tool.response
- allowed tools, denied tools
- task.start / task.end (success + failure)
- handoff event
- retry logic (tool raises retryable error, then succeeds)
- structured error object
- max_tool_calls_per_run budget behavior (optional)
- flush()
"""

from __future__ import annotations

import os
import time
from typing import Dict

from r3fresh import ALM


def main() -> None:
    # You can optionally set these for testing version propagation:
    agent_version = os.getenv("ALM_AGENT_VERSION", "1.0.0-dev")
    policy_version = os.getenv("ALM_POLICY_VERSION", "policy-dev-1")

    # If you implemented budget limiting, set small number to verify behavior.
    # If not implemented yet, set to None or remove.
    alm = ALM(
        agent_id="toy-agent-full",
        env="development",
        mode="stdout",
        agent_version=agent_version,
        policy_version=policy_version,
        denied_tools={"dangerous_tool"},
        default_allow=True,
        max_tool_calls_per_run=50,  # adjust lower if you want to test budget exhaustion
    )

    # -------------------------
    # Tools
    # -------------------------

    @alm.tool("safe_tool")
    def safe_tool(message: str) -> str:
        """Echo tool to test normal allowed execution."""
        return f"Safe: {message}"

    @alm.tool("dangerous_tool")
    def dangerous_tool(action: str) -> str:
        """Should be denied by policy."""
        return f"Dangerous action: {action}"

    # Retry test: fail twice with TimeoutError, then succeed.
    _retry_state: Dict[str, int] = {"calls": 0}

    @alm.tool("flaky_tool")
    def flaky_tool(resource: str) -> str:
        """
        Simulates a transient failure.
        Raises TimeoutError on first two calls, then returns success.
        """
        _retry_state["calls"] += 1
        if _retry_state["calls"] <= 2:
            raise TimeoutError(f"Simulated timeout talking to {resource}")
        return f"Fetched {resource} after retries"

    @alm.tool("non_retryable_fail")
    def non_retryable_fail() -> None:
        """Always fails with a non-retryable error."""
        raise ValueError("Simulated non-retryable failure")

    # -------------------------
    # Run
    # -------------------------
    with alm.run(purpose="Exercise ALM SDK full feature set"):
        # Task 1: success path with a safe tool call
        with alm.task(task_type="demo", description="Happy path task"):
            print("Calling safe_tool...")
            print(safe_tool("Hello, World!"))

        # Task 2: denied tool (policy enforcement)
        with alm.task(task_type="demo", description="Denied tool task"):
            print("\nTrying dangerous_tool (should be denied)...")
            try:
                print(dangerous_tool("delete everything"))
            except PermissionError as e:
                print(f"Expected deny: {e}")

        # Task 3: retry path
        with alm.task(task_type="demo", description="Retry logic task"):
            print("\nCalling flaky_tool (should retry then succeed)...")
            # If your SDK retries automatically, this should succeed without the caller looping.
            # If you haven't implemented retries yet, you will see the exception and can add a
            # manual retry loop here temporarily.
            try:
                print(flaky_tool("example_resource"))
            except TimeoutError as e:
                # If auto-retry is not implemented yet, fall back to manual retry so you can
                # still validate event emission structure.
                print(f"Auto-retry not active (caught): {e}")
                for i in range(3):
                    try:
                        time.sleep(0.05)
                        print(flaky_tool("example_resource"))
                        break
                    except TimeoutError as e2:
                        print(f"Manual retry {i+1} failed: {e2}")

        # Task 4: non-retryable error path
        with alm.task(task_type="demo", description="Non-retryable error task"):
            print("\nCalling non_retryable_fail (should error)...")
            try:
                non_retryable_fail()
            except ValueError as e:
                print(f"Expected error: {e}")

        # Handoff event
        print("\nEmitting handoff...")
        alm.handoff(
            to_agent_id="toy-agent-specialist",
            reason="Demonstrate handoff event emission",
            context={"ticket_id": "TICKET-123", "notes": "Needs specialist review"},
        )

        # Additional safe tool call (verifies normal flow continues)
        with alm.task(task_type="demo", description="Final task"):
            print("\nCalling safe_tool again...")
            print(safe_tool("Goodbye!"))

    # Flush remaining events
    alm.flush()
    print("\nToy agent full test completed. Inspect stdout JSON events.")


if __name__ == "__main__":
    main()
