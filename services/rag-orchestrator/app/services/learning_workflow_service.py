from __future__ import annotations

from ..core.flow_logger import log_flow
from ..models.message_model import MessageModel
from ..models.session_model import SessionModel
from ..repositories.learning_memory_repository import LearningMemoryRepository
from .exercise_grader_service import ExerciseGraderService
from .learning_coordinator_service import LearningCoordinatorService
from .session_manager_service import SessionManagerService


class LearningWorkflowService:
    """Own grading, snapshot persistence, and next-step messaging in learning mode."""

    def __init__(
        self,
        *,
        session_manager_service: SessionManagerService,
        learning_memory_repository: LearningMemoryRepository,
        exercise_grader_service: ExerciseGraderService,
    ) -> None:
        self._session_manager_service = session_manager_service
        self._learning_memory_repository = learning_memory_repository
        self._exercise_grader_service = exercise_grader_service

    async def handle_answer(
        self,
        *,
        session_model: SessionModel,
        message: str,
        embedding: list[float],
    ) -> MessageModel:
        if not session_model.tuning_plan:
            raise ValueError("Learning plan not initialized")

        learning_coordinator_service = LearningCoordinatorService(
            plan=session_model.tuning_plan,
            index=session_model.current_concept_index,
        )
        current_concept = learning_coordinator_service.current_node()
        log_flow(
            "rag-orchestrator",
            "learning.evaluation.started",
            "RAG orchestrator started evaluating the learner answer for the current learning concept.",
            session_id=session_model.id,
            concept_id=current_concept["concept_id"],
            concept_name=current_concept["concept_name"],
        )
        evaluation = await self._exercise_grader_service.evaluate(current_concept, message)
        learning_status = "complete" if evaluation["passed"] else "needs_revision"
        session_model = self._session_manager_service.record_learning_outcome(
            session_model,
            concept_id=current_concept["concept_id"],
            status=learning_status,
            feedback=evaluation["feedback"],
        )

        await self._learning_memory_repository.store_snapshot(
            session_id=session_model.id,
            snapshot={
                "concept_id": current_concept["concept_id"],
                "concept_name": current_concept["concept_name"],
                "status": learning_status,
                "feedback": evaluation["feedback"],
                "answer": message,
                "score": evaluation.get("score"),
                "highlights": evaluation.get("highlights", []),
            },
            embedding=embedding if evaluation["passed"] else None,
        )
        log_flow(
            "rag-orchestrator",
            "learning.evaluation.completed",
            "RAG orchestrator finished evaluating the learner answer and persisted the concept snapshot.",
            session_id=session_model.id,
            concept_id=current_concept["concept_id"],
            passed=evaluation["passed"],
            score=evaluation.get("score"),
        )

        if evaluation["passed"]:
            session_model = self._session_manager_service.advance_concept(session_model)
            next_index = learning_coordinator_service.next_index()
            if next_index is not None and session_model.phase != "learning_complete":
                learning_coordinator_service = LearningCoordinatorService(
                    plan=session_model.tuning_plan,
                    index=session_model.current_concept_index,
                )
                content = (
                    "Marked previous concept complete. Here's the next concept to focus on:\n\n"
                    + learning_coordinator_service.build_overview()
                )
                metadata = {
                    "phase": session_model.phase,
                    "stage": "learning_next",
                    "concept_id": learning_coordinator_service.current_node()["concept_id"],
                    "score": evaluation.get("score"),
                }
            else:
                content = (
                    "Congratulations! You've completed all planned concepts. We'll capture a final summary next."
                )
                metadata = {
                    "phase": session_model.phase,
                    "stage": "learning_complete",
                    "score": evaluation.get("score"),
                }
        else:
            content = (
                evaluation["feedback"]
                + "\n\nRevise your answer considering the exercise criteria and resubmit when ready."
            )
            metadata = {
                "phase": session_model.phase,
                "stage": "learning_retry",
                "concept_id": current_concept["concept_id"],
                "score": evaluation.get("score"),
            }

        return MessageModel(
            role="assistant",
            content=content,
            metadata=metadata,
        )
