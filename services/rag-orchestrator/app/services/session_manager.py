from __future__ import annotations

from datetime import datetime
import uuid
from typing import Dict

from ..models.session import Message, Session
from ..core.flow_logger import log_flow


class SessionManager:
    _shared_store: Dict[str, Session] = {}

    def __init__(self, store: Dict[str, Session] | None = None) -> None:
        self._store: Dict[str, Session] = store if store is not None else self._shared_store

    def create_session(
        self,
        goal: str,
        profile: dict | None = None,
        calibration_questions: list[str] | None = None,
    ) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(id=session_id, goal=goal, profile=profile or {})
        session.append(Message(role="system", content="Session initialized."))
        session.calibration_queue = list(calibration_questions or [])
        session.calibration_history = []

        self._store[session_id] = session
        log_flow(
            "rag-orchestrator",
            "session.created",
            "SessionManager created a new in-memory learning session.",
            session_id=session_id,
            goal=goal,
            has_profile=bool(profile),
            calibration_questions=len(session.calibration_queue),
        )
        return session

    def register_session(self, session: Session) -> Session:
        self._store[session.id] = session
        log_flow(
            "rag-orchestrator",
            "session.registered",
            "SessionManager registered a session loaded from persistent storage.",
            session_id=session.id,
            phase=session.phase,
        )
        return session

    def next_calibration_question(self, session_id: str) -> str | None:
        session = self._require_session(session_id)
        if not session.calibration_queue:
            log_flow(
                "rag-orchestrator",
                "calibration.question.exhausted",
                "No more calibration questions remain for this session.",
                session_id=session_id,
            )
            return None
        question = session.calibration_queue.pop(0)
        session.calibration_history.append(
            {
                "question": question,
                "answer": None,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        log_flow(
            "rag-orchestrator",
            "calibration.question.selected",
            "SessionManager selected the next calibration question.",
            session_id=session_id,
            question=question,
            remaining_questions=len(session.calibration_queue),
        )
        return question

    def record_calibration_answer(self, session_id: str, answer: str) -> None:
        session = self._require_session(session_id)
        if not session.calibration_history:
            return
        if session.calibration_history[-1].get("answer") is None:
            session.calibration_history[-1]["answer"] = answer
            log_flow(
                "rag-orchestrator",
                "calibration.answer.recorded",
                "SessionManager stored the learner answer for the current calibration question.",
                session_id=session_id,
                answer=answer,
            )

    def add_message(self, session_id: str, message: Message) -> Session:
        session = self._require_session(session_id)
        session.append(message)
        log_flow(
            "rag-orchestrator",
            "message.appended",
            "SessionManager appended a message to the session transcript.",
            session_id=session_id,
            role=message.role,
            phase=session.phase,
            metadata=message.metadata or {},
            content=message.content,
        )
        return session

    def get_session(self, session_id: str) -> Session:
        return self._require_session(session_id)

    def set_tuning_plan(self, session_id: str, plan: list[dict]) -> Session:
        session = self._require_session(session_id)
        session.tuning_plan = plan
        session.phase = "tuning"
        session.current_concept_index = 0
        session.learning_progress = []
        log_flow(
            "rag-orchestrator",
            "tuning.plan.created",
            "SessionManager stored the generated tuning roadmap on the session.",
            session_id=session_id,
            concepts=len(plan),
        )
        return session

    def begin_learning(self, session_id: str) -> Session:
        session = self._require_session(session_id)
        if not session.tuning_plan:
            raise ValueError("No tuning plan defined for session")
        session.phase = "learning"
        session.current_concept_index = 0
        session.learning_progress = []
        log_flow(
            "rag-orchestrator",
            "learning.started",
            "SessionManager moved the session from tuning into the learning phase.",
            session_id=session_id,
            concepts=len(session.tuning_plan),
        )
        return session

    def record_learning_outcome(
        self,
        session_id: str,
        concept_id: str,
        status: str,
        feedback: str,
    ) -> Session:
        session = self._require_session(session_id)
        session.learning_progress.append(
            {
                "concept_id": concept_id,
                "status": status,
                "feedback": feedback,
            }
        )
        log_flow(
            "rag-orchestrator",
            "learning.outcome.recorded",
            "SessionManager recorded the learning outcome for the current concept.",
            session_id=session_id,
            concept_id=concept_id,
            status=status,
        )
        return session

    def advance_concept(self, session_id: str) -> Session:
        session = self._require_session(session_id)
        session.current_concept_index += 1
        if session.current_concept_index >= len(session.tuning_plan):
            session.phase = "learning_complete"
        log_flow(
            "rag-orchestrator",
            "learning.concept.advanced",
            "SessionManager advanced the learner to the next concept or completed the program.",
            session_id=session_id,
            current_concept_index=session.current_concept_index,
            phase=session.phase,
        )
        return session

    def _require_session(self, session_id: str) -> Session:
        session = self._store.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")
        return session
