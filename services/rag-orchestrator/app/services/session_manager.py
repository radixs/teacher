from __future__ import annotations

import uuid
from typing import Dict

from ..models.session import Message, Session
from .calibration import CalibrationPlanner


class SessionManager:
    _shared_store: Dict[str, Session] = {}

    def __init__(self, store: Dict[str, Session] | None = None) -> None:
        self._store: Dict[str, Session] = store if store is not None else self._shared_store

    def create_session(self, goal: str, profile: dict | None = None) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(id=session_id, goal=goal, profile=profile or {})
        session.append(Message(role="system", content="Session initialized."))

        planner = CalibrationPlanner(goal=goal, profile=profile)
        session.calibration_queue = planner.questions()
        session.calibration_history = []

        self._store[session_id] = session
        return session

    def next_calibration_question(self, session_id: str) -> str | None:
        session = self._require_session(session_id)
        if not session.calibration_queue:
            return None
        question = session.calibration_queue.pop(0)
        session.calibration_history.append({"question": question, "answer": None})
        return question

    def record_calibration_answer(self, session_id: str, answer: str) -> None:
        session = self._require_session(session_id)
        if not session.calibration_history:
            return
        if session.calibration_history[-1].get("answer") is None:
            session.calibration_history[-1]["answer"] = answer

    def add_message(self, session_id: str, message: Message) -> Session:
        session = self._require_session(session_id)
        session.append(message)
        return session

    def get_session(self, session_id: str) -> Session:
        return self._require_session(session_id)

    def set_tuning_plan(self, session_id: str, plan: list[dict]) -> Session:
        session = self._require_session(session_id)
        session.tuning_plan = plan
        session.phase = "tuning"
        session.current_concept_index = 0
        session.learning_progress = []
        return session

    def begin_learning(self, session_id: str) -> Session:
        session = self._require_session(session_id)
        if not session.tuning_plan:
            raise ValueError("No tuning plan defined for session")
        session.phase = "learning"
        session.current_concept_index = 0
        session.learning_progress = []
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
        return session

    def advance_concept(self, session_id: str) -> Session:
        session = self._require_session(session_id)
        session.current_concept_index += 1
        if session.current_concept_index >= len(session.tuning_plan):
            session.phase = "learning_complete"
        return session

    def _require_session(self, session_id: str) -> Session:
        session = self._store.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")
        return session
