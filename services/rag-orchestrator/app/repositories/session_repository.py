from __future__ import annotations

from typing import List

from ..clients.elasticsearch_client import ElasticsearchClient
from ..core.flow_logger import log_flow
from ..mappers.session_document_mapper import (
    deserialize_session_document,
    serialize_session_model,
)
from ..models.session_model import SessionModel


class SessionRepository:
    def __init__(self, elasticsearch_client: ElasticsearchClient, index: str) -> None:
        self._elasticsearch_client = elasticsearch_client
        self._index = index

    async def save(self, session_model: SessionModel) -> None:
        session_document = serialize_session_model(session_model)
        await self._elasticsearch_client.upsert_document(
            self._index,
            session_model.id,
            session_document,
        )
        log_flow(
            "rag-orchestrator",
            "session_repository.saved",
            "SessionRepository persisted the full session document to Elasticsearch.",
            index=self._index,
            session_id=session_model.id,
            phase=session_model.phase,
            message_count=len(session_model.messages),
        )

    async def get(self, session_id: str) -> SessionModel | None:
        session_document = await self._elasticsearch_client.get_document(
            self._index,
            session_id,
        )
        if not session_document:
            log_flow(
                "rag-orchestrator",
                "session_repository.miss",
                "SessionRepository could not find the requested session in Elasticsearch.",
                index=self._index,
                session_id=session_id,
            )
            return None
        log_flow(
            "rag-orchestrator",
            "session_repository.hit",
            "SessionRepository loaded a session document from Elasticsearch.",
            index=self._index,
            session_id=session_id,
            phase=session_document.get("phase"),
        )
        return deserialize_session_document(session_document)

    async def list(self) -> List[SessionModel]:
        query = {"match_all": {}}
        session_documents = await self._elasticsearch_client.search(
            self._index,
            query,
            size=500,
        )
        log_flow(
            "rag-orchestrator",
            "session_repository.list",
            "SessionRepository listed persisted sessions during startup hydration.",
            index=self._index,
            count=len(session_documents),
        )
        return [
            deserialize_session_document(session_document)
            for session_document in session_documents
        ]
