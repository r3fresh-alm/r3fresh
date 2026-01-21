"""Toy agent example demonstrating ALM SDK usage."""
from alm_sdk import ALM


def main():
    """Run the toy agent example."""
    # Initialize ALM in stdout mode
    alm = ALM(
        agent_id="toy-agent-1",
        env="development",
        mode="stdout",
        # Deny the dangerous_tool to demonstrate deny behavior
        denied_tools={"dangerous_tool"},
    )

    # Define two tools

    @alm.tool("safe_tool")
    def safe_tool(message: str) -> str:
        """A safe tool that just echoes a message."""
        return f"Safe: {message}"

    @alm.tool("dangerous_tool")
    def dangerous_tool(action: str) -> str:
        """A dangerous tool that should be denied."""
        return f"Dangerous action: {action}"

    # Run a run context
    with alm.run(purpose="Demonstrate ALM SDK functionality"):
        # Call the allowed tool
        print("Calling safe_tool...")
        result1 = safe_tool("Hello, World!")
        print(f"Result: {result1}")

        # Try to call the denied tool (should raise PermissionError)
        print("\nTrying to call dangerous_tool...")
        try:
            result2 = dangerous_tool("delete everything")
            print(f"Result: {result2}")
        except PermissionError as e:
            print(f"Expected error: {e}")

        # Call another safe tool
        print("\nCalling safe_tool again...")
        result3 = safe_tool("Goodbye!")
        print(f"Result: {result3}")

    # Flush any remaining events
    alm.flush()
    print("\nExample completed. Check stdout for JSON events.")


if __name__ == "__main__":
    main()
