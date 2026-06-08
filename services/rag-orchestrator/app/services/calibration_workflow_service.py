from __future__ import annotations

from ..core.flow_logger import log_flow
from ..models.message_model import MessageModel
from ..models.session_model import SessionModel
from ..repositories.learning_memory_repository import LearningMemoryRepository
from .calibration_planner_service import CalibrationPlannerService
from .session_manager_service import SessionManagerService
from .tuning_workflow_service import TuningWorkflowService


class CalibrationWorkflowService:
    """Own the calibration-phase behavior for an active learner session."""

    def __init__(
        self,
        *,
        session_manager_service: SessionManagerService,
        learning_memory_repository: LearningMemoryRepository,
        tuning_workflow_service: TuningWorkflowService,
    ) -> None:
        self._session_manager_service = session_manager_service
        self._learning_memory_repository = learning_memory_repository
        self._tuning_workflow_service = tuning_workflow_service

    async def handle_answer(
        self,
        *,
        session_model: SessionModel,
        message: str,
        embedding: list[float],
    ) -> MessageModel:
        session_id = session_model.id
        log_flow(
            "rag-orchestrator",
            "calibration.processing",
            "RAG orchestrator is processing the learner answer inside the calibration or tuning branch.",
            session_id=session_id,
            phase=session_model.phase,
        )

        self._session_manager_service.record_calibration_answer(session_model, message)
        calibration_history = session_model.calibration_history
        if calibration_history:
            latest_calibration_record = calibration_history[-1]
            if latest_calibration_record.get("answer"):
                calibration_planner_service = CalibrationPlannerService(
                    goal=session_model.goal,
                    profile=session_model.profile,
                )
                snapshot = calibration_planner_service.synthesize_snapshot(
                    latest_calibration_record["question"],
                    latest_calibration_record["answer"],
                )
                await self._learning_memory_repository.store_snapshot(
                    session_id=session_id,
                    snapshot=snapshot,
                    embedding=embedding,
                )
                log_flow(
                    "rag-orchestrator",
                    "calibration.snapshot.created",
                    "RAG orchestrator synthesized a knowledge snapshot from the latest calibration answer.",
                    session_id=session_id,
                    question=latest_calibration_record["question"],
                )

        next_question = self._session_manager_service.next_calibration_question(session_model)
        if next_question:
            assistant_message_model = MessageModel(
                role="assistant",
                content=next_question,
                metadata={"phase": session_model.phase, "stage": "calibration"},
            )
            log_flow(
                "rag-orchestrator",
                "calibration.next_question",
                "RAG orchestrator asked the next calibration question.",
                session_id=session_id,
                question=assistant_message_model.content,
            )
            return assistant_message_model

        return await self._tuning_workflow_service.complete_calibration(session_model)
