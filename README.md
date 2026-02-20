# r3fresh ALM SDK

[![PyPI - Version](https://img.shields.io/pypi/v/r3fresh.svg)](https://pypi.org/project/r3fresh)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/r3fresh.svg)](https://pypi.org/project/r3fresh)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Agent Lifecycle Management SDK** – A production-ready Python SDK for tracking AI agent execution with policy enforcement, event emission, and structured event data for downstream analytics.

## Overview

The SDK provides automatic instrumentation for AI agents, capturing:
- **Tool calls** with policy enforcement (allow/deny) and latency tracking
- **Run lifecycle** (`run.start` / `run.end`) with summary statistics
- **Tasks** (`task.start` / `task.end`) for logical units of work
- **Handoffs** for agent-to-agent transitions
- **Structured errors** (type, message, source, retryable) in tool and run events
- **Version tracking** (schema, SDK, agent, policy) on every event

All events are emitted automatically. They can be sent to **stdout** (development) or an **HTTP endpoint** (production). The SDK does not perform analytics itself; it produces events for your backend or analytics pipeline.

## Getting Started

To use r3fresh in production with cloud analytics:

1. **Sign up** at [r3fresh.dev](https://r3fresh.dev)
2. **Get your API key** from the [Dashboard](https://r3fresh.dev/dashboard)
3. **Install the SDK**: `pip install r3fresh`
4. **Integrate** using the examples below

The r3fresh platform provides:
- **Real-time monitoring** dashboard for all your agents
- **Analytics** with run history, tool usage, and performance metrics
- **Code Assistant** - AI-powered tool to automatically integrate r3fresh into your existing code
- **Policy management** and quota tracking

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
    mode="stdout",  # or "http" with endpoint (base URL)
    agent_version="1.0.0",
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
    agent_id="unique-agent-id",       # Required: Unique identifier
    env="production",                 # Environment name
    mode="http",                      # "stdout" or "http"
    endpoint="https://api.r3fresh.dev",  # r3fresh platform API (or your own backend)
    api_key="your-api-key",           # Get from https://r3fresh.dev/dashboard
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
- Latency tracking (`policy_latency_ms`, `tool_latency_ms`, `total_latency_ms`)
- Structured errors (type, message, source, retryable) on failure or deny
- `attempt` and `retries` in events (retry infrastructure exists but retries are disabled by default)

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
- **Run lifecycle**: `run.start`, `run.end` (with summary stats in `run.end` metadata)
- **Tool execution**: `tool.request`, `policy.decision`, `tool.response` (including `status="denied"` when blocked)
- **Task tracking**: `task.start`, `task.end`
- **Handoffs**: `handoff` events

Every event includes a unique `event_id` (UUID) for idempotency and deduplication.

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

Errors in `tool.response` and `run.end` are structured as:
- `type`, `message`, `source` (tool, policy, agent, system)
- `retryable` (auto-detected for e.g. `ConnectionError`, `TimeoutError`, or when "timeout" appears in the message)
- `code` (optional)

Example (in `tool.response` metadata or `run.end` metadata):

```json
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

Every `run.end` event includes `metadata.summary`:

```json
{
    "metadata": {
        "success": true,
        "summary": {
            "tool_calls": { "total": 10, "allowed": 8, "denied": 1, "error": 1, "retried": 2 },
            "latencies": { "avg_tool_ms": 50.2, "avg_policy_ms": 0.5, "total_run_ms": 1500.0 },
            "tasks": { "completed": 3, "failed": 1 },
            "handoffs": 1
        }
    }
}
```

On run failure, `metadata.error` contains the structured error object.

### Retries

The SDK records `attempt` and `retries` on tool events and marks errors as `retryable` when appropriate. Automatic retries are **not** enabled by default (`max_retries=0`). The infrastructure is in place for future use or custom retry logic.

## API Reference

### ALM Class

#### `__init__(...)`

Initialize an ALM instance.

**Parameters:**
- `agent_id` (str, required): Unique agent identifier
- `env` (str, default="development"): Environment name
- `mode` (str, default="stdout"): Event sink mode ("stdout" or "http")
- `endpoint` (str, optional): Base URL for HTTP mode (required if `mode="http"`). The SDK POSTs to `/v1/events`. For the r3fresh platform, use `https://api.r3fresh.dev`.
- `api_key` (str, optional): API key for authentication. Get yours at [r3fresh.dev/dashboard](https://r3fresh.dev/dashboard). Sent as `Authorization: Bearer <api_key>`.
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
    endpoint="https://api.r3fresh.dev",
    api_key="your-api-key",
    agent_version="1.0.0",
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
    max_tool_calls_per_run=20,
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

### Error Handling

```python
alm = ALM(agent_id="api-agent", mode="stdout")

@alm.tool("api_call")
def api_call(url: str):
    """API call that may fail."""
    response = httpx.get(url, timeout=5.0)
    response.raise_for_status()
    return response.json()

with alm.run():
    try:
        result = api_call("https://api.example.com/data")
    except Exception:
        # SDK already emitted tool.response with status="error" and structured error
        pass
```

## Event Schema

All events share a common shape. Timestamps are RFC3339 (e.g. `2026-01-21T12:00:00.123Z`).

```json
{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-01-21T12:00:00.123Z",
    "event_type": "tool.request",
    "agent_id": "agent-123",
    "env": "production",
    "run_id": "run-456",
    "schema_version": "1.0",
    "sdk_version": "0.1.0",
    "agent_version": "1.0.0",
    "policy_version": "2.0.0",
    "metadata": {}
}
```

`event_id` is a UUID per event for idempotency and deduplication.

### Event Types

- `run.start`: Run started
- `run.end`: Run finished (includes `metadata.summary` and optionally `metadata.error`)
- `tool.request`: Tool call initiated (`metadata` includes `tool_name`, `tool_call_id`, `args`, etc.)
- `policy.decision`: Allow or deny (`metadata.decision`, `metadata.tool_call_id`, `metadata.latency_ms`)
- `tool.response`: Tool completed (`metadata.status`: `success`, `denied`, or `error`; latencies, `attempt`, `retries`)
- `task.start`: Task started
- `task.end`: Task finished (success/failure, optional `metadata.error`)
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

For production with the r3fresh platform:

```python
alm = ALM(
    agent_id="prod-agent",
    mode="http",
    endpoint="https://api.r3fresh.dev",  # r3fresh platform API
    api_key=os.getenv("ALM_API_KEY"),    # Get from https://r3fresh.dev/dashboard
    agent_version=__version__,
)
```

Events are batched (default 50) and POSTed to `{endpoint}/v1/events`. The SDK:
- Buffers events and flushes on batch size or at run end
- Catches flush failures so the agent does not crash
- Sends `Authorization: Bearer <api_key>` when `api_key` is set

**Self-hosted option:** You can also run your own event ingestion API. The SDK will POST events to any endpoint that accepts the r3fresh event schema at `/v1/events`.

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

## Resources

- **Website**: [r3fresh.dev](https://r3fresh.dev)
- **Documentation**: [r3fresh.dev/docs](https://r3fresh.dev/docs)
- **Dashboard**: [r3fresh.dev/dashboard](https://r3fresh.dev/dashboard)
- **Code Assistant**: [r3fresh.dev/dashboard/code-assistant](https://r3fresh.dev/dashboard/code-assistant) - AI-powered integration helper
- **GitHub**: [github.com/r3fresh-alm/r3fresh](https://github.com/r3fresh-alm/r3fresh)

## License

`r3fresh` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Support

For issues, questions, or feature requests:
- Email: [support@r3fresh.dev](mailto:support@r3fresh.dev)
- GitHub Issues: [github.com/r3fresh-alm/r3fresh/issues](https://github.com/r3fresh-alm/r3fresh/issues)
