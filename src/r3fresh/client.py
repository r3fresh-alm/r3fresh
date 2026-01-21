# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Event client for ALM SDK."""
import json
import sys
from typing import List, Optional

import httpx

from .events import Event


class EventClient:
    """Client for emitting events to stdout or HTTP endpoint."""

    def __init__(
        self,
        mode: str = "stdout",
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        batch_size: int = 50,
    ):
        """Initialize event client.

        Args:
            mode: "stdout" or "http"
            endpoint: HTTP endpoint URL (required for http mode)
            api_key: API key for HTTP authentication
            batch_size: Number of events to batch before flushing
        """
        if mode not in ("stdout", "http"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'stdout' or 'http'")
        if mode == "http" and not endpoint:
            raise ValueError("endpoint is required for http mode")

        self.mode = mode
        self.endpoint = endpoint
        self.api_key = api_key
        self.batch_size = batch_size
        self._queue: List[Event] = []
        self._http_client: Optional[httpx.Client] = None

        if mode == "http":
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            self._http_client = httpx.Client(
                base_url=endpoint.rstrip("/"),
                headers=headers,
                timeout=10.0,
            )

    def emit(self, event: Event) -> None:
        """Add an event to the queue and flush if batch size reached."""
        self._queue.append(event)
        if len(self._queue) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        """Flush queued events to stdout or HTTP endpoint."""
        if not self._queue:
            return

        try:
            if self.mode == "stdout":
                self._flush_stdout()
            else:
                self._flush_http()
        except Exception as e:
            # Must not crash agent if server is down
            # In stdout mode, this shouldn't happen, but catch anyway
            print(f"ALM SDK: Failed to flush events: {e}", file=sys.stderr)
        finally:
            self._queue.clear()

    def _flush_stdout(self) -> None:
        """Flush events to stdout as JSON lines."""
        # Create a copy of the queue to avoid any mutation issues
        events_to_flush = list(self._queue)
        for event in events_to_flush:
            # model_dump() creates a new dict, ensuring immutability
            event_dict = event.model_dump(mode='json')
            print(json.dumps(event_dict, ensure_ascii=False), flush=True)

    def _flush_http(self) -> None:
        """Flush events to HTTP endpoint."""
        if not self._http_client:
            return

        # model_dump() creates new dicts, ensuring immutability
        events_data = [event.model_dump(mode='json') for event in self._queue]
        response = self._http_client.post(
            "/v1/events",
            json={"events": events_data},
        )
        response.raise_for_status()

    def close(self) -> None:
        """Close the HTTP client if in http mode."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush and close."""
        self.flush()
        self.close()
