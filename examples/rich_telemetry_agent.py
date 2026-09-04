"""Provider-neutral manual LLM, retrieval, and evaluation instrumentation."""
from r3fresh import ALM
from r3fresh.telemetry import TelemetryConfig

alm = ALM(
    "research-agent",
    telemetry=TelemetryConfig(
        context={"deployment_id": "deploy-42", "git_sha": "abc123", "workflow_version": "research-v2"},
    ),
)


@alm.tool(
    "knowledge_base_lookup",
    telemetry={
        "dependency_name": "knowledge-base",
        "dependency_type": "internal_api",
        "http_method": "POST",
        "endpoint_host": "knowledge.internal",
        "timeout_ms": 2_000,
    },
)
def knowledge_base_lookup(topic):
    """Representative dependency call; arguments and result stay private by default."""
    return {"documents": 5, "topic": topic}


with alm.run(purpose="Research", metadata={"customer_tier": "enterprise"}):
    with alm.task("research", metadata={"topic_category": "technical"}):
        alm.llm_request(provider="openai", model="example-model", temperature=0.2)
        alm.llm_response(
            provider="openai", model="example-model", input_tokens=18240, output_tokens=920,
            time_to_first_token_ms=420, generation_latency_ms=2100, total_latency_ms=2520,
            estimated_cost_usd=0.084, finish_reason="stop",
        )
        alm.retrieval_request(retriever_name="knowledge-base", vector_store="pgvector", top_k=5)
        alm.retrieval_response(
            retriever_name="knowledge-base", documents_returned=5, chunks_returned=12,
            average_similarity_score=0.86, retrieved_tokens=3400, retrieval_latency_ms=44,
            cache_hit=False, status="success",
        )
        knowledge_base_lookup("r3fresh telemetry")
        alm.evaluation_result(
            evaluator_name="groundedness-check", evaluator_type="deterministic",
            score=0.92, threshold=0.8, passed=True, groundedness=0.92,
        )
