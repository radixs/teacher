from __future__ import annotations

"""HTTP endpoints for session-related FastAPI requests."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from ...core.service_container import get_user_workflow_service
from ...core.flow_logger import log_flow
from ...dto.session_message_request_dto import SessionMessageRequestDto
from ...dto.session_message_response_dto import SessionMessageResponseDto
from ...dto.session_response_dto import SessionResponseDto
from ...dto.session_start_request_dto import SessionStartRequestDto
from ...mappers.session_response_mapper import (
    to_session_message_response_dto,
    to_session_response_dto,
)
from ...services.calibration_question_generation_error import (
    CalibrationQuestionGenerationError,
)
from ...services.embedding_generation_error import EmbeddingGenerationError
from ...services.exercise_grading_error import ExerciseGradingError
from ...services.external_search_error import ExternalSearchError
from ...services.learning_plan_not_initialized_error import (
    LearningPlanNotInitializedError,
)
from ...services.llm_generation_error import LlmGenerationError
from ...services.session_not_found_error import SessionNotFoundError
from ...services.tuning_plan_generation_error import TuningPlanGenerationError
from ...services.user_workflow_service import UserWorkflowService

router = APIRouter(prefix="/sessions", tags=["sessions"])

SessionStartRequestBody = Annotated[SessionStartRequestDto, Body(..., embed=False)]
SessionMessageRequestBody = Annotated[SessionMessageRequestDto, Body(..., embed=False)]
UserWorkflowServiceDependency = Annotated[
    UserWorkflowService,
    Depends(get_user_workflow_service),
]


def _preview(value: str | None) -> str | None:
    """Trim long message content before writing it into boundary logs."""
    if value is None:
        return None
    return value if len(value) <= 140 else value[:137] + "..."


@router.post("", response_model=SessionResponseDto)
async def post_session(
    session_start_request_dto: SessionStartRequestBody,
    user_workflow_service: UserWorkflowServiceDependency,
) -> SessionResponseDto:
    """Start a new learning session and return the serialized session state."""
    log_flow(
        "rag-orchestrator",
        "api.sessions.start.received",
        "RAG orchestrator received a request to start a new learning session.",
        goal=session_start_request_dto.goal,
        has_profile=bool(session_start_request_dto.profile),
    )

    try:
        session_model = await user_workflow_service.start_new_session(
            goal=session_start_request_dto.goal,
            profile=session_start_request_dto.profile,
        )
    except (
        CalibrationQuestionGenerationError,
        EmbeddingGenerationError,
        LlmGenerationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    log_flow(
        "rag-orchestrator",
        "api.sessions.start.completed",
        "RAG orchestrator initialized the session, stored the first assistant turn, and persisted the session.",
        session_id=session_model.id,
        phase=session_model.phase,
    )
    return to_session_response_dto(session_model)


@router.post("/{session_id}", response_model=SessionMessageResponseDto)
async def post_message(
    session_id: str,
    session_message_request_dto: SessionMessageRequestBody,
    user_workflow_service: UserWorkflowServiceDependency,
) -> SessionMessageResponseDto:
    """Accept one learner turn and return the assistant reply plus session state."""
    log_flow(
        "rag-orchestrator",
        "api.sessions.message.received",
        "RAG orchestrator received a learner message for an existing session.",
        session_id=session_id,
        message_preview=_preview(session_message_request_dto.message),
        has_metadata=bool(session_message_request_dto.metadata),
    )

    try:
        session_message_result = await user_workflow_service.send_message(
            session_id=session_id,
            message=session_message_request_dto.message,
            metadata=session_message_request_dto.metadata,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LearningPlanNotInitializedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (
        CalibrationQuestionGenerationError,
        TuningPlanGenerationError,
        ExerciseGradingError,
        EmbeddingGenerationError,
        ExternalSearchError,
        LlmGenerationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    log_flow(
        "rag-orchestrator",
        "api.sessions.message.completed",
        "RAG orchestrator finished processing the learner message and returned the assistant turn.",
        session_id=session_id,
        phase=session_message_result.session.phase,
        stage=(session_message_result.last_message.metadata or {}).get("stage"),
    )
    return to_session_message_response_dto(
        session_model=session_message_result.session,
        last_message_model=session_message_result.last_message,
    )


@router.get("/{session_id}", response_model=SessionResponseDto)
async def get_session(
    session_id: str,
    user_workflow_service: UserWorkflowServiceDependency,
) -> SessionResponseDto:
    """Load a session by id, restoring it from persistence when needed."""
    log_flow(
        "rag-orchestrator",
        "api.sessions.show.received",
        "RAG orchestrator received a request to load a stored session by id.",
        session_id=session_id,
    )

    try:
        session_model = await user_workflow_service.get_session(session_id=session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    log_flow(
        "rag-orchestrator",
        "api.sessions.show.completed",
        "RAG orchestrator returned the stored session payload.",
        session_id=session_id,
        phase=session_model.phase,
    )
    return to_session_response_dto(session_model)
