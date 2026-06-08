from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, Dict

from ..models.message_model import MessageModel
from ..models.session_model import SessionModel
from ..core.flow_logger import log_flow


class SessionManagerService:
    _shared_store: Dict[str, SessionModel] = {}

    def __init__(self, store: Dict[str, SessionModel] | None = None) -> None:
        self._store: Dict[str, SessionModel] = store if store is not None else self._shared_store

    def create_session(
        self,
        goal: str,
        profile: dict[str, Any] | None = None,
        calibration_questions: list[str] | None = None,
    ) -> SessionModel:
        session_id = str(uuid.uuid4())
        session_model = SessionModel(id=session_id, goal=goal, profile=profile or {})
        session_model.append(MessageModel(role="system", content="Session initialized."))
        session_model.calibration_queue = list(calibration_questions or [])
        session_model.calibration_history = []

        self._store[session_id] = session_model
        log_flow(
            "rag-orchestrator",
            "session.created",
            "SessionManagerService created a new in-memory learning session.",
            session_id=session_id,
            goal=goal,
            has_profile=bool(profile),
            calibration_questions=len(session_model.calibration_queue),
        )
        return session_model

    def load_session(self, session_model: SessionModel) -> SessionModel:
        self._store[session_model.id] = session_model
        log_flow(
            "rag-orchestrator",
            "session.loaded",
            "SessionManagerService loaded a session from persistent storage into memory.",
            session_id=session_model.id,
            phase=session_model.phase,
        )
        return session_model

    def next_calibration_question(self, session_model: SessionModel) -> str | None:
        session_id = session_model.id
        if not session_model.calibration_queue:
            log_flow(
                "rag-orchestrator",
                "calibration.question.exhausted",
                "No more calibration questions remain for this session.",
                session_id=session_id,
            )
            return None
        question = session_model.calibration_queue.pop(0)
        session_model.calibration_history.append(
            {
                "question": question,
                "answer": None,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        log_flow(
            "rag-orchestrator",
            "calibration.question.selected",
            "SessionManagerService selected the next calibration question.",
            session_id=session_id,
            question=question,
            remaining_questions=len(session_model.calibration_queue),
        )
        return question

    def record_calibration_answer(self, session_model: SessionModel, answer: str) -> None:
        session_id = session_model.id
        if not session_model.calibration_history:
            return
        if session_model.calibration_history[-1].get("answer") is None:
            session_model.calibration_history[-1]["answer"] = answer
            log_flow(
                "rag-orchestrator",
                "calibration.answer.recorded",
                "SessionManagerService stored the learner answer for the current calibration question.",
                session_id=session_id,
                answer=answer,
            )

    def add_message(
        self,
        session_model: SessionModel,
        message_model: MessageModel,
    ) -> SessionModel:
        session_id = session_model.id
        session_model.append(message_model)
        log_flow(
            "rag-orchestrator",
            "message.appended",
            "SessionManagerService appended a message to the session transcript.",
            session_id=session_id,
            role=message_model.role,
            phase=session_model.phase,
            metadata=message_model.metadata or {},
            content=message_model.content,
        )
        return session_model

    def get_session(self, session_id: str) -> SessionModel:
        return self._require_session(session_id)

    def set_tuning_plan(
        self,
        session_model: SessionModel,
        plan: list[dict[str, Any]],
    ) -> SessionModel:
        session_id = session_model.id
        session_model.tuning_plan = plan
        session_model.phase = "tuning"
        session_model.current_concept_index = 0
        session_model.learning_progress = []
        log_flow(
            "rag-orchestrator",
            "tuning.plan.created",
            "SessionManagerService stored the generated tuning roadmap on the session.",
            session_id=session_id,
            concepts=len(plan),
        )
        return session_model

    def begin_learning(self, session_model: SessionModel) -> SessionModel:
        session_id = session_model.id
        if not session_model.tuning_plan:
            raise ValueError("No tuning plan defined for session")
        session_model.phase = "learning"
        session_model.current_concept_index = 0
        session_model.learning_progress = []
        log_flow(
            "rag-orchestrator",
            "learning.started",
            "SessionManagerService moved the session from tuning into the learning phase.",
            session_id=session_id,
            concepts=len(session_model.tuning_plan),
        )
        return session_model

    def record_learning_outcome(
        self,
        session_model: SessionModel,
        concept_id: str,
        status: str,
        feedback: str,
    ) -> SessionModel:
        session_id = session_model.id
        session_model.learning_progress.append(
            {
                "concept_id": concept_id,
                "status": status,
                "feedback": feedback,
            }
        )
        log_flow(
            "rag-orchestrator",
            "learning.outcome.recorded",
            "SessionManagerService recorded the learning outcome for the current concept.",
            session_id=session_id,
            concept_id=concept_id,
            status=status,
        )
        return session_model

    def advance_concept(self, session_model: SessionModel) -> SessionModel:
        session_id = session_model.id
        session_model.current_concept_index += 1
        if session_model.current_concept_index >= len(session_model.tuning_plan):
            session_model.phase = "learning_complete"
        log_flow(
            "rag-orchestrator",
            "learning.concept.advanced",
            "SessionManagerService advanced the learner to the next concept or completed the program.",
            session_id=session_id,
            current_concept_index=session_model.current_concept_index,
            phase=session_model.phase,
        )
        return session_model

    def _require_session(self, session_id: str) -> SessionModel:
        session_model = self._store.get(session_id)
        if not session_model:
            raise KeyError(f"Session {session_id} not found")
        return session_model
