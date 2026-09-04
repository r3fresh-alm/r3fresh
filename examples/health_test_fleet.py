"""Controlled temporary agents for validating r3fresh health metrics.

Defaults to stdout so it never sends data to a live API accidentally. Set
ALM_MODE=http, ALM_ENDPOINT, and ALM_API_KEY to send the same known workload to
a dedicated test organization.
"""
from __future__ import annotations

import os
import time

from r3fresh import ALM


MODE = os.getenv("ALM_MODE", "stdout")
ENDPOINT = os.getenv("ALM_ENDPOINT")
API_KEY = os.getenv("ALM_API_KEY")
ENV = os.getenv("ALM_ENV", "health-test")
RUNS_PER_AGENT = int(os.getenv("ALM_TEST_RUNS", "20"))


def make_agent(agent_id: str, *, allowed_tools: set[str], denied_tools: set[str] | None = None) -> ALM:
    return ALM(
        agent_id=agent_id,
        env=ENV,
        mode=MODE,
        endpoint=ENDPOINT,
        api_key=API_KEY,
        agent_version="health-test-v1",
        policy_version="health-test-policy-v1",
        allowed_tools=allowed_tools,
        denied_tools=denied_tools or set(),
        default_allow=False,
    )


def run_healthy() -> None:
    agent = make_agent("test-healthy-agent", allowed_tools={"lookup"})

    @agent.tool("lookup")
    def lookup() -> str:
        return "ok"

    for _ in range(RUNS_PER_AGENT):
        with agent.run(purpose="Health baseline"):
            lookup()


def run_slow() -> None:
    agent = make_agent("test-slow-agent", allowed_tools={"slow_lookup"})

    @agent.tool("slow_lookup")
    def slow_lookup() -> str:
        time.sleep(0.25)
        return "slow but successful"

    for _ in range(RUNS_PER_AGENT):
        with agent.run(purpose="Latency threshold test"):
            slow_lookup()


def run_flaky() -> None:
    agent = make_agent("test-flaky-agent", allowed_tools={"unstable_lookup"})
    attempt = 0

    @agent.tool("unstable_lookup")
    def unstable_lookup() -> str:
        nonlocal attempt
        attempt += 1
        if attempt % 2:
            raise ConnectionError("Intentional transient test failure")
        return "recovered"

    for _ in range(RUNS_PER_AGENT):
        try:
            with agent.run(purpose="Reliability threshold test"):
                unstable_lookup()
        except ConnectionError:
            # The run context records this as a failed run before continuing.
            pass


def run_policy() -> None:
    agent = make_agent(
        "test-policy-agent",
        allowed_tools={"approved_tool"},
        denied_tools={"blocked_tool"},
    )

    @agent.tool("blocked_tool")
    def blocked_tool() -> None:
        raise AssertionError("A blocked tool must never execute")

    for _ in range(RUNS_PER_AGENT):
        with agent.run(purpose="Policy threshold test"):
            try:
                blocked_tool()
            except PermissionError:
                pass


def run_handoff() -> None:
    source = make_agent("test-handoff-source", allowed_tools={"prepare"})
    target = make_agent("test-handoff-target", allowed_tools={"complete"})

    @source.tool("prepare")
    def prepare() -> str:
        return "handoff-ready"

    @target.tool("complete")
    def complete() -> str:
        return "handoff-complete"

    for _ in range(RUNS_PER_AGENT):
        with source.run(purpose="Handoff source test"):
            prepare()
            source.handoff(
                to_agent_id="test-handoff-target",
                reason="Controlled handoff validation",
                context={"test_run": True},
            )
        with target.run(purpose="Handoff target test"):
            complete()


def main() -> None:
    if MODE == "http" and (not ENDPOINT or not API_KEY):
        raise SystemExit("ALM_MODE=http requires ALM_ENDPOINT and ALM_API_KEY")

    print(f"Running {RUNS_PER_AGENT} controlled runs per test agent in {MODE!r} mode")
    run_healthy()
    run_slow()
    run_flaky()
    run_policy()
    run_handoff()
    print("Test fleet complete")


if __name__ == "__main__":
    main()
