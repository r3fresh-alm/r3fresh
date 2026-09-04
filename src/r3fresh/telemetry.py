"""Configuration for optional r3fresh telemetry capture."""
from dataclasses import dataclass, field
from typing import Any, Dict


_INFRASTRUCTURE_CONTEXT_KEYS = {
    "cloud_provider",
    "cluster",
    "container_id",
    "host",
    "hostname",
    "instance_id",
    "namespace",
    "region",
    "runtime",
    "service_instance",
    "zone",
}


@dataclass
class TelemetryConfig:
    """Controls optional payload capture and shared event context.

    Identifiers and operational metrics are always safe to emit. Potentially
    sensitive payloads require an explicit opt-in.
    """

    redact_sensitive_data: bool = True
    capture_inputs: bool = False
    capture_outputs: bool = False
    capture_prompts: bool = False
    capture_tool_results: bool = False
    capture_infrastructure: bool = False
    context: Dict[str, Any] = field(default_factory=dict)

    def event_context(self) -> Dict[str, Any]:
        """Return an event-safe copy of explicitly configured shared context."""
        if self.capture_infrastructure:
            return dict(self.context)

        # Deployment identifiers can expose topology; emit them only on opt-in.
        return {
            key: value
            for key, value in self.context.items()
            if key.lower() not in _INFRASTRUCTURE_CONTEXT_KEYS
        }
