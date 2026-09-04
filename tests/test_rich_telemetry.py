import json
from contextlib import redirect_stdout
from io import StringIO

from r3fresh import ALM
from r3fresh.telemetry import TelemetryConfig


def _events(output):
    return [json.loads(line) for line in output.getvalue().splitlines() if line.startswith("{")]


def test_rich_telemetry_is_optional_private_and_aggregated():
    output = StringIO()
    config = TelemetryConfig(context={"deployment_id": "deploy-1", "git_sha": "abc123"})
    alm = ALM("telemetry-agent", telemetry=config)

    with redirect_stdout(output):
        with alm.run(purpose="research", metadata={"customer_tier": "enterprise"}):
            alm.llm_request(provider="openai", model="example", prompt="secret prompt")
            alm.llm_response(provider="openai", model="example", input_tokens=10,
                             output_tokens=5, estimated_cost_usd=0.02, retries=1)
            alm.retrieval_request(retriever_name="docs", query="private query")
            alm.retrieval_response(retriever_name="docs", documents_returned=3,
                                   retrieval_latency_ms=12.5, cache_hit=True)
            alm.evaluation_result(evaluator_name="human", score=0.9, passed=True,
                                  feedback="private feedback")

    events = _events(output)
    by_type = {event["event_type"]: event for event in events}
    assert {"llm.request", "llm.response", "retrieval.request", "retrieval.response", "evaluation.result"} <= set(by_type)
    assert "prompt" not in by_type["llm.request"]["metadata"]
    assert "query" not in by_type["retrieval.request"]["metadata"]
    assert "feedback" not in by_type["evaluation.result"]["metadata"]
    assert by_type["llm.response"]["metadata"]["total_tokens"] == 15
    assert by_type["llm.response"]["context"]["deployment_id"] == "deploy-1"

    summary = by_type["run.end"]["metadata"]["summary"]
    assert summary["llm"] == {
        "calls": 1, "input_tokens": 10, "output_tokens": 5,
        "total_tokens": 15, "estimated_cost_usd": 0.02,
    }
    assert summary["retrieval"] == {"calls": 1}
    assert summary["retries"] == 1


def test_sensitive_inputs_can_be_explicitly_enabled_and_redacted():
    output = StringIO()
    config = TelemetryConfig(capture_prompts=True, capture_inputs=True)
    alm = ALM("private-agent", telemetry=config)

    with redirect_stdout(output):
        with alm.run():
            alm.llm_request(prompt={"api_key": "do-not-store", "question": "safe"})
            alm.retrieval_request(query="visible query")

    by_type = {event["event_type"]: event for event in _events(output)}
    assert by_type["llm.request"]["metadata"]["prompt"]["api_key"] == "***REDACTED***"
    assert by_type["retrieval.request"]["metadata"]["query"] == "visible query"


def test_tool_metadata_and_infrastructure_context_are_opt_in():
    output = StringIO()
    config = TelemetryConfig(context={"region": "us-west-2", "deployment_id": "deploy-2"})
    alm = ALM("tool-agent", telemetry=config)

    @alm.tool(
        telemetry={"dependency_name": "billing", "http_method": "POST", "http_status": 201},
    )
    def create_invoice(customer_id):
        return {"customer_id": customer_id, "authorization": "private"}

    with redirect_stdout(output):
        with alm.run():
            create_invoice("customer-1")

    by_type = {event["event_type"]: event for event in _events(output)}
    assert by_type["tool.request"]["metadata"]["args"] == {}
    assert by_type["tool.request"]["metadata"]["telemetry"]["dependency_name"] == "billing"
    assert "result" not in by_type["tool.response"]["metadata"]
    assert "region" not in by_type["tool.request"]["context"]
    assert by_type["tool.request"]["context"]["deployment_id"] == "deploy-2"

    output = StringIO()
    infra_alm = ALM(
        "infra-agent",
        telemetry=TelemetryConfig(capture_infrastructure=True, context={"region": "us-west-2"}),
    )
    with redirect_stdout(output):
        with infra_alm.run():
            pass
    assert _events(output)[0]["context"]["region"] == "us-west-2"
