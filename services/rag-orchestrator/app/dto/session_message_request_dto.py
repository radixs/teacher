from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SessionMessageRequestDto(BaseModel):
    message: str = Field(..., min_length=1)
    metadata: dict[str, Any] | None = None

