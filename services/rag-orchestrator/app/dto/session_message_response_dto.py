from __future__ import annotations

from pydantic import BaseModel

from .message_response_dto import MessageResponseDto
from .session_response_dto import SessionResponseDto


class SessionMessageResponseDto(BaseModel):
    session: SessionResponseDto
    last_message: MessageResponseDto

