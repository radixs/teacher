from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SessionStartRequestDto(BaseModel):
    goal: str = Field(..., min_length=3)
    profile: dict[str, Any] | None = None

