# SPDX-FileCopyrightText: 2026-present r3fresh <support@r3fresh.dev>
#
# SPDX-License-Identifier: MIT
"""Structured error handling for ALM SDK."""
from typing import Optional

from pydantic import BaseModel, Field


class Error(BaseModel):
    """Structured error object."""

    type: str = Field(..., description="Error type/class name")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code if available")
    retryable: bool = Field(False, description="Whether the error is retryable")
    source: str = Field("tool", description="Source of error: tool, policy, agent, system")
    details: Optional[dict] = Field(None, description="Additional error details")

    def to_dict(self) -> dict:
        """Convert error to dictionary."""
        return self.model_dump(exclude_none=True)
