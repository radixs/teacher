from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MessageResponseDto(BaseModel):
    role: str
    content: str
    created_at: datetime
    metadata: dict[str, Any] | None = None

