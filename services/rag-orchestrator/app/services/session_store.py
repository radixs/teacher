from __future__ import annotations

from datetime import datetime
from typing import List

from ..clients.elasticsearch import ElasticsearchClient
from ..core.flow_logger import log_flow
from ..models.session import Message, Session


def _serialize_message(message: Message) -> dict:
    return {
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "metadata": message.metadata or {},
    }


def _deserialize_message(payload: dict) -> Message:
    created_at = payload.get("created_at")
    timestamp = datetime.fromisoformat(created_at) if created_at else datetime.utcnow()
    return Message(
        role=payload.get("role", "assistant"),
        content=payload.get("content", ""),
        created_at=timestamp,
        metadata=payload.get("metadata") or {},
    )


def _serialize_session(session: Session) -> dict:
    return {
        "id": session.id,
        "goal": session.goal,
        "profile": session.profile or {},
        "phase": session.phase,
        "messages": [_serialize_message(msg) for msg in session.messages],
        "calibration_queue": session.calibration_queue,
        "calibration_history": session.calibration_history,
        "tuning_plan": session.tuning_plan,
        "current_concept_index": session.current_concept_index,
        "learning_progress": session.learning_progress,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _deserialize_session(payload: dict) -> Session:
    created_at = payload.get("created_at")
    updated_at = payload.get("updated_at")
    session = Session(
        id=payload["id"],
        goal=payload.get("goal", ""),
        profile=payload.get("profile") or {},
        phase=payload.get("phase", "calibration"),
        messages=[_deserialize_message(item) for item in payload.get("messages", [])],
        calibration_queue=list(payload.get("calibration_queue", [])),
        calibration_history=list(payload.get("calibration_history", [])),
        tuning_plan=list(payload.get("tuning_plan", [])),
        current_concept_index=int(payload.get("current_concept_index", 0)),
        learning_progress=list(payload.get("learning_progress", [])),
        created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow(),
        updated_at=datetime.fromisoformat(updated_at) if updated_at else datetime.utcnow(),
    )
    return session


class SessionStore:
    def __init__(self, client: ElasticsearchClient, index: str) -> None:
        self._client = client
        self._index = index

    async def save(self, session: Session) -> None:
        document = _serialize_session(session)
        await self._client.upsert_document(self._index, session.id, document)
        log_flow(
            "rag-orchestrator",
            "session_store.saved",
            "SessionStore persisted the full session document to Elasticsearch.",
            index=self._index,
            session_id=session.id,
            phase=session.phase,
            message_count=len(session.messages),
        )

    async def get(self, session_id: str) -> Session | None:
        payload = await self._client.get_document(self._index, session_id)
        if not payload:
            log_flow(
                "rag-orchestrator",
                "session_store.miss",
                "SessionStore could not find the requested session in Elasticsearch.",
                index=self._index,
                session_id=session_id,
            )
            return None
        log_flow(
            "rag-orchestrator",
            "session_store.hit",
            "SessionStore loaded a session document from Elasticsearch.",
            index=self._index,
            session_id=session_id,
            phase=payload.get("phase"),
        )
        return _deserialize_session(payload)

    async def list(self) -> List[Session]:
        query = {"match_all": {}}
        payload = await self._client.search(self._index, query, size=500)
        log_flow(
            "rag-orchestrator",
            "session_store.list",
            "SessionStore listed persisted sessions during startup hydration.",
            index=self._index,
            count=len(payload),
        )
        return [_deserialize_session(item) for item in payload]
