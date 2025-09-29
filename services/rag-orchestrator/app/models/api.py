from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class SessionStartRequest(BaseModel):
    goal: str = Field(..., min_length=3)
    profile: Optional[dict[str, Any]] = None


class SessionMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    metadata: Optional[dict[str, Any]] = None


class MessageModel(BaseModel):
    role: str
    content: str
    created_at: datetime
    metadata: Optional[dict[str, Any]] = None


class SessionModel(BaseModel):
    id: str
    goal: str
    phase: str
    profile: dict[str, Any]
    messages: List[MessageModel]
    created_at: datetime
    updated_at: datetime


class SessionMessageResponse(BaseModel):
    session: SessionModel
    last_message: MessageModel
