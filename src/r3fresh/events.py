# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Event objects for ALM SDK."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from .__about__ import __version__ as SDK_VERSION

# Schema version - increment when event structure changes
SCHEMA_VERSION = "1.1"


class Event(BaseModel):
    """Base event with common fields."""

    event_id: str = Field(..., description="Unique event ID (UUID) for idempotency and deduplication")
    timestamp: str = Field(..., description="RFC3339 timestamp")
    event_type: str = Field(..., description="Type of event")
    agent_id: str = Field(..., description="Agent identifier")
    env: str = Field(..., description="Environment name")
    run_id: Optional[str] = Field(None, description="Run identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    # Version tracking fields
    schema_version: str = Field(default=SCHEMA_VERSION, description="Event schema version")
    sdk_version: str = Field(default=SDK_VERSION, description="SDK version")
    agent_version: Optional[str] = Field(None, description="Agent version")
    policy_version: Optional[str] = Field(None, description="Policy version")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional deployment and execution context",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2026-01-01T00:00:00.000Z",
                "event_type": "run.start",
                "agent_id": "agent-123",
                "env": "production",
                "run_id": "run-456",
                "metadata": {},
            }
        }
    )


def run_start_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: str,
    purpose: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a run.start event."""
    metadata: Dict[str, Any] = {}
    if purpose:
        metadata["purpose"] = purpose
    if custom_metadata:
        metadata["custom"] = custom_metadata
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="run.start",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def llm_request_event(
    event_id: str, timestamp: str, agent_id: str, env: str, run_id: Optional[str],
    provider: Optional[str] = None, model: Optional[str] = None,
    streaming: Optional[bool] = None, temperature: Optional[float] = None,
    max_tokens: Optional[int] = None, attempt: int = 1,
    prompt: Optional[Any] = None, custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None, policy_version: Optional[str] = None,
) -> Event:
    """Create an LLM request event for manual provider instrumentation."""
    metadata = _metadata(
        provider=provider, model=model, streaming=streaming, temperature=temperature,
        max_tokens=max_tokens, attempt=attempt, prompt=prompt,
        custom_metadata=custom_metadata,
    )
    return _event(
        event_id, timestamp, "llm.request", agent_id, env, run_id, metadata,
        agent_version, policy_version,
    )


def llm_response_event(
    event_id: str, timestamp: str, agent_id: str, env: str, run_id: Optional[str],
    provider: Optional[str] = None, model: Optional[str] = None,
    input_tokens: Optional[int] = None, output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None, context_tokens: Optional[int] = None,
    context_window_size: Optional[int] = None,
    context_window_used_pct: Optional[float] = None,
    time_to_first_token_ms: Optional[float] = None,
    generation_latency_ms: Optional[float] = None,
    total_latency_ms: Optional[float] = None,
    estimated_cost_usd: Optional[float] = None, streaming: Optional[bool] = None,
    temperature: Optional[float] = None, max_tokens: Optional[int] = None,
    finish_reason: Optional[str] = None, attempt: int = 1, retries: int = 0,
    error: Optional[Dict[str, Any]] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None, policy_version: Optional[str] = None,
) -> Event:
    """Create an LLM response event with optional usage and cost metrics."""
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if context_window_used_pct is None and context_tokens is not None and context_window_size:
        context_window_used_pct = round((context_tokens / context_window_size) * 100, 2)
    metadata = _metadata(
        provider=provider, model=model, input_tokens=input_tokens,
        output_tokens=output_tokens, total_tokens=total_tokens,
        context_tokens=context_tokens, context_window_size=context_window_size,
        context_window_used_pct=context_window_used_pct,
        time_to_first_token_ms=time_to_first_token_ms,
        generation_latency_ms=generation_latency_ms, total_latency_ms=total_latency_ms,
        estimated_cost_usd=estimated_cost_usd, streaming=streaming,
        temperature=temperature, max_tokens=max_tokens, finish_reason=finish_reason,
        attempt=attempt, retries=retries, error=error, custom_metadata=custom_metadata,
    )
    return _event(
        event_id, timestamp, "llm.response", agent_id, env, run_id, metadata,
        agent_version, policy_version,
    )


def retrieval_request_event(
    event_id: str, timestamp: str, agent_id: str, env: str, run_id: Optional[str],
    retriever_name: Optional[str] = None, vector_store: Optional[str] = None,
    top_k: Optional[int] = None, filters: Optional[Dict[str, Any]] = None,
    query: Optional[Any] = None, custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None, policy_version: Optional[str] = None,
) -> Event:
    """Create a retrieval request event without requiring raw query capture."""
    return _event(
        event_id, timestamp, "retrieval.request", agent_id, env, run_id,
        _metadata(retriever_name=retriever_name, vector_store=vector_store, top_k=top_k,
                  filters=filters, query=query, custom_metadata=custom_metadata),
        agent_version, policy_version,
    )


def retrieval_response_event(
    event_id: str, timestamp: str, agent_id: str, env: str, run_id: Optional[str],
    retriever_name: Optional[str] = None, vector_store: Optional[str] = None,
    retrieval_latency_ms: Optional[float] = None, documents_returned: Optional[int] = None,
    chunks_returned: Optional[int] = None, similarity_scores: Optional[Any] = None,
    average_similarity_score: Optional[float] = None,
    min_similarity_score: Optional[float] = None,
    max_similarity_score: Optional[float] = None, retrieved_tokens: Optional[int] = None,
    reranker_used: Optional[bool] = None, reranker_latency_ms: Optional[float] = None,
    cache_hit: Optional[bool] = None, status: Optional[str] = None,
    error: Optional[Dict[str, Any]] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None, policy_version: Optional[str] = None,
) -> Event:
    """Create a retrieval response event with aggregate retrieval metrics."""
    return _event(
        event_id, timestamp, "retrieval.response", agent_id, env, run_id,
        _metadata(retriever_name=retriever_name, vector_store=vector_store,
                  retrieval_latency_ms=retrieval_latency_ms,
                  documents_returned=documents_returned, chunks_returned=chunks_returned,
                  similarity_scores=similarity_scores,
                  average_similarity_score=average_similarity_score,
                  min_similarity_score=min_similarity_score,
                  max_similarity_score=max_similarity_score,
                  retrieved_tokens=retrieved_tokens, reranker_used=reranker_used,
                  reranker_latency_ms=reranker_latency_ms, cache_hit=cache_hit,
                  status=status, error=error, custom_metadata=custom_metadata),
        agent_version, policy_version,
    )


def evaluation_result_event(
    event_id: str, timestamp: str, agent_id: str, env: str, run_id: Optional[str],
    evaluator_name: Optional[str] = None, evaluator_type: Optional[str] = None,
    score: Optional[float] = None, passed: Optional[bool] = None,
    threshold: Optional[float] = None, task_completed: Optional[bool] = None,
    groundedness: Optional[float] = None, correctness: Optional[float] = None,
    relevance: Optional[float] = None, user_rating: Optional[float] = None,
    feedback: Optional[str] = None, custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None, policy_version: Optional[str] = None,
) -> Event:
    """Create a generic human, deterministic, or model evaluation event."""
    return _event(
        event_id, timestamp, "evaluation.result", agent_id, env, run_id,
        _metadata(evaluator_name=evaluator_name, evaluator_type=evaluator_type,
                  score=score, passed=passed, threshold=threshold,
                  task_completed=task_completed, groundedness=groundedness,
                  correctness=correctness, relevance=relevance,
                  user_rating=user_rating, feedback=feedback,
                  custom_metadata=custom_metadata),
        agent_version, policy_version,
    )


def _metadata(custom_metadata: Optional[Dict[str, Any]] = None, **values: Any) -> Dict[str, Any]:
    metadata = {key: value for key, value in values.items() if value is not None}
    if custom_metadata:
        metadata["custom"] = custom_metadata
    return metadata


def _event(
    event_id: str, timestamp: str, event_type: str, agent_id: str, env: str,
    run_id: Optional[str], metadata: Dict[str, Any], agent_version: Optional[str],
    policy_version: Optional[str],
) -> Event:
    return Event(
        event_id=event_id, timestamp=timestamp, event_type=event_type,
        agent_id=agent_id, env=env, run_id=run_id, metadata=metadata,
        agent_version=agent_version, policy_version=policy_version,
    )


def run_end_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: str,
    success: bool,
    error: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
    # Summary fields
    tool_calls_total: int = 0,
    tool_calls_allowed: int = 0,
    tool_calls_denied: int = 0,
    tool_calls_error: int = 0,
    tool_calls_retried: int = 0,
    avg_tool_latency_ms: float = 0.0,
    avg_policy_latency_ms: float = 0.0,
    total_run_duration_ms: float = 0.0,
    tasks_completed: int = 0,
    tasks_failed: int = 0,
    handoffs: int = 0,
    total_input_tokens: int = 0,
    total_output_tokens: int = 0,
    total_tokens: int = 0,
    total_estimated_cost_usd: float = 0.0,
    total_llm_calls: int = 0,
    total_retrieval_calls: int = 0,
    retries: int = 0,
    custom_metadata: Optional[Dict[str, Any]] = None,
) -> Event:
    """Create a run.end event with summary statistics."""
    metadata: Dict[str, Any] = {
        "success": success,
        "summary": {
            "tool_calls": {
                "total": tool_calls_total,
                "allowed": tool_calls_allowed,
                "denied": tool_calls_denied,
                "error": tool_calls_error,
                "retried": tool_calls_retried,
            },
            "latencies": {
                "avg_tool_ms": avg_tool_latency_ms,
                "avg_policy_ms": avg_policy_latency_ms,
                "total_run_ms": total_run_duration_ms,
            },
            "tasks": {
                "completed": tasks_completed,
                "failed": tasks_failed,
            },
            "handoffs": handoffs,
            "llm": {
                "calls": total_llm_calls,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_usd": total_estimated_cost_usd,
            },
            "retrieval": {"calls": total_retrieval_calls},
            "retries": retries,
        },
    }
    if error:
        metadata["error"] = error
    if custom_metadata:
        metadata["custom"] = custom_metadata
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="run.end",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def tool_request_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    tool_call_id: str,
    args: Dict[str, Any],
    attempt: int = 1,
    telemetry: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a tool.request event."""
    metadata: Dict[str, Any] = {
        "tool_name": tool_name,
        "tool_call_id": tool_call_id,
        "args": args,
        "attempt": attempt,
    }
    if telemetry:
        metadata["telemetry"] = telemetry
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="tool.request",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def tool_response_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    tool_call_id: str,
    status: str,
    policy_latency_ms: float,
    tool_latency_ms: float,
    total_latency_ms: float,
    attempt: int = 1,
    retries: int = 0,
    error: Optional[Dict[str, Any]] = None,
    result: Optional[Any] = None,
    telemetry: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a tool.response event."""
    metadata: Dict[str, Any] = {
        "tool_name": tool_name,
        "tool_call_id": tool_call_id,
        "status": status,
        "policy_latency_ms": policy_latency_ms,
        "tool_latency_ms": tool_latency_ms,
        "total_latency_ms": total_latency_ms,
        "attempt": attempt,
        "retries": retries,
    }
    if error:
        metadata["error"] = error
    if result is not None:
        metadata["result"] = result
    if telemetry:
        metadata["telemetry"] = telemetry
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="tool.response",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def policy_decision_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    tool_name: str,
    tool_call_id: str,
    decision: str,
    reason: str,
    latency_ms: float,
    attempt: int = 1,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a policy.decision event."""
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="policy.decision",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata={
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "decision": decision,
            "reason": reason,
            "latency_ms": latency_ms,
            "attempt": attempt,
        },
        agent_version=agent_version,
        policy_version=policy_version,
    )


def task_start_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    task_id: str,
    task_type: Optional[str] = None,
    description: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a task.start event."""
    metadata: Dict[str, Any] = {"task_id": task_id}
    if task_type:
        metadata["task_type"] = task_type
    if description:
        metadata["description"] = description
    if custom_metadata:
        metadata["custom"] = custom_metadata
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="task.start",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def task_end_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    task_id: str,
    success: bool,
    error: Optional[Dict[str, Any]] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a task.end event."""
    metadata: Dict[str, Any] = {
        "task_id": task_id,
        "success": success,
    }
    if error:
        metadata["error"] = error
    if custom_metadata:
        metadata["custom"] = custom_metadata
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="task.end",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )


def handoff_event(
    event_id: str,
    timestamp: str,
    agent_id: str,
    env: str,
    run_id: Optional[str],
    from_agent_id: str,
    to_agent_id: str,
    reason: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    agent_version: Optional[str] = None,
    policy_version: Optional[str] = None,
) -> Event:
    """Create a handoff event."""
    metadata: Dict[str, Any] = {
        "from_agent_id": from_agent_id,
        "to_agent_id": to_agent_id,
    }
    if reason:
        metadata["reason"] = reason
    if context:
        metadata["context"] = context
    if custom_metadata:
        metadata["custom"] = custom_metadata
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        event_type="handoff",
        agent_id=agent_id,
        env=env,
        run_id=run_id,
        metadata=metadata,
        agent_version=agent_version,
        policy_version=policy_version,
    )
