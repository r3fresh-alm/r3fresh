"""Test SDK → API integration. Requires API running and ALM_API_KEY, ALM_ENDPOINT set."""
import os
import sys

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from r3fresh import ALM


def main() -> None:
    endpoint = os.getenv("ALM_ENDPOINT", "http://127.0.0.1:8000")
    api_key = os.getenv("ALM_API_KEY")
    if not api_key:
        print("ALM_API_KEY not set. Set it to your API key to test HTTP ingestion.")
        sys.exit(1)

    alm = ALM(
        agent_id="sdk-api-test-agent",
        env="development",
        mode="http",
        endpoint=endpoint,
        api_key=api_key,
        agent_version="0.1.2",
    )

    @alm.tool("test_tool")
    def test_tool(x: int) -> int:
        """Simple tool for integration test."""
        return x * 2

    print(f"Posting events to {endpoint}/v1/events ...")
    try:
        with alm.run(purpose="SDK-API integration test"):
            result = test_tool(21)
            print(f"test_tool(21) = {result}")

        alm.flush()
        print("Done. Check API logs and alm.runs / alm.tool_calls for data.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
