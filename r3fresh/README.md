# r3fresh ALM SDK

[![PyPI - Version](https://img.shields.io/pypi/v/r3fresh.svg)](https://pypi.org/project/r3fresh)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/r3fresh.svg)](https://pypi.org/project/r3fresh)

**Agent Lifecycle Management SDK** - A Python SDK for tracking, monitoring, and managing AI agent execution with policy enforcement, event tracking, and comprehensive analytics.

## Overview

The ALM SDK provides automatic instrumentation for AI agents, capturing:
- Tool calls with policy enforcement
- Run lifecycle tracking
- Task management
- Agent-to-agent handoffs
- Comprehensive metrics and analytics
- Structured error tracking with retry logic

All events are automatically captured and can be sent to stdout (for development) or HTTP endpoints (for production monitoring).

## Installation

```console
pip install r3fresh
```

Or install from source:

```console
git clone https://github.com/r3fresh-alm/r3fresh.git
cd r3fresh
pip install -e .
```

## Quick Start

```python
from r3fresh import ALM

# Initialize the SDK
alm = ALM(
    agent_id="my-agent",
    env="development",
    mode="stdout",  # or "http" with endpoint
    agent_version="1.0.0"
)

# Define tools with automatic policy enforcement
@alm.tool("search_web")
def search_web(query: str) -> str:
    """Search the web for information."""
    # Your tool implementation
    return f"Results for: {query}"

# Run your agent with automatic tracking
with alm.run(purpose="Process user query"):
    result = search_web("Python SDK documentation")
    print(result)

# All events are automatically captured and emitted
```

## Core Concepts

### ALM Instance

The `ALM` class is the main entry point that manages:
- Event collection and emission
- Policy enforcement
- Run tracking
- Version management

```python
alm = ALM(
    agent_id="unique-agent-id",      # Required: Unique identifier
    env="production",                 # Environment name
    mode="http",                      # "stdout" or "http"
    endpoint="https://api.example.com/v1/events",  # Required for http mode
    api_key="your-api-key",           # Optional: For authenticated endpoints
    agent_version="1.2.3",            # Optional: Agent version
    policy_version="2.0.0",           # Optional: Policy version
    allowed_tools={"tool1", "tool2"}, # Optional: Whitelist tools
    denied_tools={"dangerous_tool"},  # Optional: Blacklist tools
    default_allow=True,               # Allow tools by default
    max_tool_calls_per_run=100,       # Optional: Budget limit
)
```

### Runs

Runs track the execution lifecycle of an agent. All events within a run are correlated via `run_id`.

```python
with alm.run(purpose="Answer user question"):
    # Your agent logic here
    pass
# run.end event automatically emitted with summary statistics
```

### Tools

Tools are automatically instrumented with:
- Policy enforcement (allow/deny)
- Latency tracking (policy, tool, total)
- Error handling with structured errors
- Automatic retry logic for retryable errors
- Attempt and retry counting

```python
@alm.tool("my_tool")  # Optional: specify tool name
def my_tool(param1: str, param2: int) -> dict:
    """Tool documentation."""
    # Your implementation
    return {"result": "success"}
```

### Tasks

Tasks represent logical units of work within a run. They automatically emit `task.start` and `task.end` events.

```python
with alm.task(description="Process user input"):
    # Task logic
    pass
# Success/failure automatically tracked
```

### Handoffs

Handoffs represent agent-to-agent transitions:

```python
alm.handoff(
    to_agent_id="next-agent",
    reason="Requires specialized knowledge",
    context={"query": "..."}
)
```

## Features

### Automatic Event Tracking

The SDK automatically captures:
- **Run lifecycle**: `run.start`, `run.end` with summary statistics
- **Tool execution**: `tool.request`, `policy.decision`, `tool.response`
- **Task tracking**: `task.start`, `task.end`
- **Handoffs**: `handoff` events

### Policy Enforcement

Enforce tool usage policies:
- Whitelist/blacklist tools
- Budget limits per run
- Default allow/deny behavior

```python
alm = ALM(
    agent_id="agent-1",
    allowed_tools={"safe_tool", "read_tool"},  # Only these allowed
    denied_tools={"delete_tool"},              # Never allow this
    max_tool_calls_per_run=50                  # Budget limit
)
```

### Structured Error Handling

Errors are automatically structured with:
- Error type and message
- Retryability detection
- Source tracking (tool, policy, agent, system)
- Error codes (optional)

```python
# Automatic structured error in tool.response:
{
    "error": {
        "type": "ConnectionError",
        "message": "Connection timeout",
        "source": "tool",
        "retryable": true
    }
}
```

### Version Tracking

All events include version information for drift detection:
- `schema_version`: Event schema version
- `sdk_version`: SDK version
- `agent_version`: Your agent version
- `policy_version`: Your policy version

### Run Summary Statistics

Every `run.end` event includes comprehensive summary:

```json
{
    "summary": {
        "tool_calls": {
            "total": 10,
            "allowed": 8,
            "denied": 1,
            "error": 1,
            "retried": 2
        },
        "latencies": {
            "avg_tool_ms": 50.2,
            "avg_policy_ms": 0.5,
            "total_run_ms": 1500.0
        },
        "tasks": {
            "completed": 3,
            "failed": 1
        },
        "handoffs": 1
    }
}
```

### Automatic Retry Logic

The SDK includes retry infrastructure for tools. When a tool raises a retryable error (ConnectionError, TimeoutError, etc.), the error is automatically structured and marked as retryable. The retry mechanism is in place but currently disabled by default (max_retries=0). This allows for tracking retryable errors while you implement custom retry logic if needed.

## API Reference

### ALM Class

#### `__init__(...)`

Initialize an ALM instance.

**Parameters:**
- `agent_id` (str, required): Unique agent identifier
- `env` (str, default="development"): Environment name
- `mode` (str, default="stdout"): Event sink mode ("stdout" or "http")
- `endpoint` (str, optional): HTTP endpoint URL (required for http mode)
- `api_key` (str, optional): API key for HTTP authentication
- `agent_version` (str, optional): Agent version string
- `policy_version` (str, optional): Policy version string
- `allowed_tools` (Set[str], optional): Whitelist of allowed tools
- `denied_tools` (Set[str], optional): Blacklist of denied tools
- `default_allow` (bool, default=True): Allow tools by default
- `max_tool_calls_per_run` (int, optional): Maximum tool calls per run

#### `run(purpose: Optional[str] = None) -> Run`

Create a run context manager. Returns a `Run` instance that tracks all events within the run.

#### `tool(tool_name: Optional[str] = None)`

Decorator factory for wrapping tool functions with automatic instrumentation.

#### `task(task_type: Optional[str] = None, description: Optional[str] = None) -> TaskContext`

Create a task context manager for tracking task execution.

#### `handoff(to_agent_id: str, reason: Optional[str] = None, context: Optional[Dict] = None)`

Emit a handoff event for agent-to-agent transitions.

#### `flush()`

Flush queued events to the configured sink.

## Examples

### Basic Agent with Tools

```python
from r3fresh import ALM

alm = ALM(
    agent_id="research-agent",
    env="production",
    mode="http",
    endpoint="https://api.example.com/v1/events",
    api_key="your-api-key",
    agent_version="1.0.0"
)

@alm.tool("search")
def search(query: str) -> str:
    """Search the web."""
    # Implementation
    return "results"

@alm.tool("summarize")
def summarize(text: str) -> str:
    """Summarize text."""
    # Implementation
    return "summary"

with alm.run(purpose="Research and summarize"):
    results = search("Python SDK")
    summary = summarize(results)
    print(summary)
```

### Policy Enforcement

```python
alm = ALM(
    agent_id="controlled-agent",
    denied_tools={"delete", "modify"},
    allowed_tools={"read", "search"},
    max_tool_calls_per_run=20
)

@alm.tool("delete")
def delete_item(item_id: str):
    """This will be denied."""
    pass

with alm.run():
    try:
        delete_item("123")  # Raises PermissionError
    except PermissionError as e:
        print(f"Blocked: {e}")
```

### Task Management

```python
alm = ALM(agent_id="task-agent", mode="stdout")

with alm.run():
    with alm.task(description="Process input"):
        # Task logic
        pass
    
    with alm.task(description="Generate output"):
        # Task logic
        pass
```

### Agent Handoffs

```python
alm = ALM(agent_id="coordinator", mode="stdout")

with alm.run():
    # Do some work
    if needs_specialist:
        alm.handoff(
            to_agent_id="specialist-agent",
            reason="Requires domain expertise",
            context={"query": user_query}
        )
```

### Error Handling and Retries

```python
@alm.tool("api_call")
def api_call(endpoint: str):
    """API call that may fail."""
    response = httpx.get(endpoint, timeout=5.0)
    response.raise_for_status()
    return response.json()

# Errors are automatically structured and marked as retryable
# The SDK tracks retryable errors for monitoring and analytics
try:
    result = api_call("https://api.example.com/data")
except Exception as e:
    # Handle the error - SDK has already logged it with retryable flag
    pass
```

## Event Schema

All events follow a consistent schema:

```json
{
    "timestamp": "2026-01-21T12:00:00Z",
    "event_type": "tool.request",
    "agent_id": "agent-123",
    "env": "production",
    "run_id": "run-456",
    "schema_version": "1.0",
    "sdk_version": "0.0.3",
    "agent_version": "1.0.0",
    "policy_version": "2.0.0",
    "metadata": {
        // Event-specific metadata
    }
}
```

### Event Types

- `run.start`: Run initialization
- `run.end`: Run completion with summary
- `tool.request`: Tool call initiated
- `policy.decision`: Policy decision (allow/deny)
- `tool.response`: Tool call completion
- `task.start`: Task initialization
- `task.end`: Task completion
- `handoff`: Agent-to-agent handoff

## Development Mode

For development, use `mode="stdout"` to see events as JSON lines:

```python
alm = ALM(agent_id="dev-agent", mode="stdout")

with alm.run():
    @alm.tool("test_tool")
    def test_tool(x: int) -> int:
        return x * 2
    
    result = test_tool(5)
```

Output:
```json
{"event_type": "run.start", ...}
{"event_type": "tool.request", ...}
{"event_type": "tool.response", ...}
{"event_type": "run.end", ...}
```

## Production Mode

For production, use `mode="http"` with your backend endpoint:

```python
alm = ALM(
    agent_id="prod-agent",
    mode="http",
    endpoint="https://api.yourcompany.com/v1/events",
    api_key=os.getenv("ALM_API_KEY"),
    agent_version=__version__
)
```

Events are automatically batched and sent to the endpoint. The SDK handles:
- Automatic batching (50 events default)
- Error handling (won't crash your agent)
- Authentication headers
- Retry logic

## Testing

Run the test suite:

```console
pytest
```

Run the example:

```console
python examples/toy_agent.py
```

## Requirements

- Python 3.8+
- pydantic
- httpx

## License

`r3fresh` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Support

For issues, questions, or feature requests, please contact support@r3fresh.dev.
