from __future__ import annotations

import uuid
from typing import Dict

from ..models.session import Message, Session


class SessionManager:
    def __init__(self) -> None:
        self._store: Dict[str, Session] = {}

    def create_session(self, goal: str, profile: dict | None = None) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(id=session_id, goal=goal, profile=profile or {})
        session.append(Message(role="system", content="Session initialized."))
        self._store[session_id] = session
        return session

    def add_message(self, session_id: str, message: Message) -> Session:
        session = self._require_session(session_id)
        session.append(message)
        return session

    def get_session(self, session_id: str) -> Session:
        return self._require_session(session_id)

    def _require_session(self, session_id: str) -> Session:
        session = self._store.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")
        return session
