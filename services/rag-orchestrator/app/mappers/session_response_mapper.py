from __future__ import annotations

"""Response mapping helpers that translate internal models into DTOs."""

from ..dto.message_response_dto import MessageResponseDto
from ..dto.session_message_response_dto import SessionMessageResponseDto
from ..dto.session_response_dto import SessionResponseDto
from ..models.message_model import MessageModel
from ..models.session_model import SessionModel


def to_message_response_dto(message_model: MessageModel) -> MessageResponseDto:
    """Convert one internal transcript message into the public API response DTO."""
    return MessageResponseDto(
        role=message_model.role,
        content=message_model.content,
        created_at=message_model.created_at,
        metadata=message_model.metadata,
    )


def to_session_response_dto(session_model: SessionModel) -> SessionResponseDto:
    """Convert a full internal session aggregate into the API response DTO."""
    return SessionResponseDto(
        id=session_model.id,
        goal=session_model.goal,
        phase=session_model.phase,
        profile=session_model.profile or {},
        messages=[
            to_message_response_dto(message_model)
            for message_model in session_model.messages
        ],
        created_at=session_model.created_at,
        updated_at=session_model.updated_at,
        tuning_plan=session_model.tuning_plan or [],
    )


def to_session_message_response_dto(
    *,
    session_model: SessionModel,
    last_message_model: MessageModel,
) -> SessionMessageResponseDto:
    """Build the compound response returned by the message endpoint."""
    return SessionMessageResponseDto(
        session=to_session_response_dto(session_model),
        last_message=to_message_response_dto(last_message_model),
    )

