from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .message_response_dto import MessageResponseDto


class SessionResponseDto(BaseModel):
    id: str
    goal: str
    phase: str
    profile: dict[str, Any]
    messages: list[MessageResponseDto]
    created_at: datetime
    updated_at: datetime
    tuning_plan: list[dict[str, Any]] | None = None

