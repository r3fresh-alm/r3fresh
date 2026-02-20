"""
Toy agent for r3fresh ALM SDK

What this tests:
- run.start / run.end with summary stats
- tool.request / policy.decision / tool.response
- allow/deny policy (denied tool raises PermissionError)
- tool latency visibility (simulated sleeps)
- task.start / task.end
- handoff event
- structured errors on tool failure
"""

from __future__ import annotations

import os
import time
from typing import Dict, Any
from dotenv import load_dotenv

from r3fresh import ALM

load_dotenv()


def main() -> None:
    # Toggle these to test different sinks
    mode = os.getenv("ALM_MODE", "stdout")  # "stdout" or "http"
    endpoint = os.getenv("ALM_ENDPOINT")    # required if mode == "http"
    api_key = os.getenv("ALM_API_KEY")      # optional

    alm = ALM(
        agent_id="toy-agent-1",
        env=os.getenv("ALM_ENV", "development"),
        mode=mode,
        endpoint=endpoint,
        api_key=api_key,
        agent_version="0.0.1-toy",
        policy_version="0.0.1-policy",
        # Demonstrate policy behavior:
        allowed_tools={"safe_tool", "flaky_tool", "slow_tool"},  # whitelist
        denied_tools={"dangerous_tool"},                         # blacklist
        default_allow=False,                                     # enforce whitelist
        max_tool_calls_per_run=25,
    )

    # Tools

    @alm.tool("safe_tool")
    def safe_tool(message: str) -> str:
        """Always succeeds; quick tool."""
        return f"Safe: {message}"

    @alm.tool("slow_tool")
    def slow_tool(ms: int) -> str:
        """Sleeps to make tool latency visible."""
        time.sleep(ms / 1000.0)
        return f"Slept {ms}ms"

    @alm.tool("flaky_tool")
    def flaky_tool(should_fail: bool) -> Dict[str, Any]:
        """Fails on demand to test structured error capture."""
        if should_fail:
            raise ConnectionError("Simulated connection timeout")
        return {"ok": True}

    @alm.tool("dangerous_tool")
    def dangerous_tool() -> None:
        """Should be denied by policy."""
        raise RuntimeError("If you see this, policy did not deny the tool!")

    # Agent logic

    print(f"Mode: {mode}")
    if mode == "http":
        print(f"Endpoint: {endpoint!r} (SDK should POST to {endpoint}/v1/events)")

    with alm.run(purpose="Toy agent smoke test"):
        # Task 1: happy path tools
        with alm.task(description="Happy path tools"):
            print("Calling safe_tool...")
            print(safe_tool("Hello, World!"))

            print("Calling slow_tool...")
            print(slow_tool(150))

        # Task 2: denied tool
        with alm.task(description="Policy deny test"):
            print("\nTrying to call dangerous_tool...")
            try:
                dangerous_tool()
            except PermissionError as e:
                print(f"Expected error: {e}")

        # Task 3: error capture
        with alm.task(description="Error capture test"):
            print("\nCalling flaky_tool (forced failure)...")
            try:
                flaky_tool(True)
            except Exception as e:
                print(f"Expected failure: {type(e).__name__}: {e}")

        alm.handoff(
            to_agent_id="next-agent",
            reason="Demonstrate handoff event emission",
            context={"note": "handoff triggered after tests"},
        )

    try:
        alm.flush()
    except Exception:
        pass


if __name__ == "__main__":
    main()
