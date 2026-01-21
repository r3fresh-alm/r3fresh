# SPDX-FileCopyrightText: 2026-present zengjosh <zeng080407@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Run context manager for ALM SDK."""
from typing import Optional

from .events import run_end_event, run_start_event
from .util import safe_error, utc_now_iso


class Run:
    """Context manager for agent runs."""

    def __init__(self, alm_instance: "ALM", purpose: Optional[str] = None):  # noqa: F821
        """Initialize a run.

        Args:
            alm_instance: The ALM instance that owns this run
            purpose: Optional purpose description for the run
        """
        self.alm = alm_instance
        self.run_id = None
        self.purpose = purpose
        self._started = False

    def __enter__(self):
        """Enter the run context - emit run.start event."""
        self.run_id = self.alm._new_run_id()
        self._started = True

        event = run_start_event(
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.run_id,
            purpose=self.purpose,
        )
        self.alm.client.emit(event)

        # Reset policy budget at start of new run
        self.alm.policy.reset_budget()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the run context - emit run.end event."""
        if not self._started:
            return

        success = exc_type is None
        error = None
        if exc_val is not None:
            error_dict = safe_error(exc_val)
            error = f"{error_dict['type']}: {error_dict['message']}"

        event = run_end_event(
            timestamp=utc_now_iso(),
            agent_id=self.alm.agent_id,
            env=self.alm.env,
            run_id=self.run_id,
            success=success,
            error=error,
        )
        self.alm.client.emit(event)

        # Flush events at end of run
        self.alm.flush()

        # Return False to not suppress exceptions
        return False
