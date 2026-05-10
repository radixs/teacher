from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from ..core.flow_logger import log_flow


class ElasticsearchClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def store_interaction(
        self,
        index: str,
        session_id: str,
        role: str,
        content: str,
        turn: int,
        embedding: list[float] | None = None,
        metadata: Optional[Dict[str, Any]] = None,
        phase: str | None = None,
    ) -> None:
        document: Dict[str, Any] = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "turn": turn,
            "metadata": metadata or {},
            "phase": phase,
            "created_at": datetime.utcnow().isoformat(),
        }
        if embedding:
            document["embedding"] = embedding

        await self._client.post(f"/{index}/_doc", json=document)
        log_flow(
            "elasticsearch",
            "interaction.stored",
            "RAG orchestrator stored a session interaction document in Elasticsearch.",
            index=index,
            session_id=session_id,
            role=role,
            turn=turn,
            phase=phase,
            has_embedding=bool(embedding),
        )

    async def store_snapshot(
        self,
        index: str,
        session_id: str,
        snapshot: Dict[str, Any],
        embedding: list[float] | None = None,
    ) -> None:
        payload = dict(snapshot)
        payload.update(
            {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        if embedding:
            payload["embedding"] = embedding

        await self._client.post(f"/{index}/_doc", json=payload)
        log_flow(
            "elasticsearch",
            "snapshot.stored",
            "RAG orchestrator stored a knowledge snapshot document in Elasticsearch.",
            index=index,
            session_id=session_id,
            has_embedding=bool(embedding),
            snapshot_keys=sorted(payload.keys()),
        )

    async def store_dependency_node(self, index: str, node: Dict[str, Any]) -> None:
        payload = dict(node)
        payload.setdefault("created_at", datetime.utcnow().isoformat())
        await self._client.post(f"/{index}/_doc", json=payload)
        log_flow(
            "elasticsearch",
            "dependency_node.stored",
            "RAG orchestrator stored a dependency graph node in Elasticsearch.",
            index=index,
            concept_id=payload.get("concept_id"),
            concept_name=payload.get("concept_name"),
        )

    async def store_learning_resource(
        self,
        index: str,
        resource: Dict[str, Any],
        embedding: list[float] | None = None,
    ) -> None:
        payload = dict(resource)
        payload.setdefault("created_at", datetime.utcnow().isoformat())
        if embedding:
            payload["embedding"] = embedding
        await self._client.post(f"/{index}/_doc", json=payload)
        log_flow(
            "elasticsearch",
            "learning_resource.stored",
            "RAG orchestrator stored a learning resource document in Elasticsearch.",
            index=index,
            title=payload.get("title"),
            url=payload.get("url"),
            has_embedding=bool(embedding),
        )

    async def upsert_user_profile(
        self,
        index: str,
        document_id: str,
        goal: str,
        experience_summary: str,
        knowledge_vector: list[float] | None = None,
    ) -> None:
        timestamp = datetime.utcnow().isoformat()
        payload: Dict[str, Any] = {
            "user_id": document_id,
            "goal": goal,
            "experience_summary": experience_summary,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        if knowledge_vector:
            payload["knowledge_vector"] = knowledge_vector
        await self._client.put(f"/{index}/_doc/{document_id}", json=payload)
        log_flow(
            "elasticsearch",
            "user_profile.upserted",
            "RAG orchestrator upserted a learner profile document in Elasticsearch.",
            index=index,
            user_id=document_id,
            has_vector=bool(knowledge_vector),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def upsert_document(self, index: str, document_id: str, document: Dict[str, Any]) -> None:
        await self._client.put(f"/{index}/_doc/{document_id}", json=document)
        log_flow(
            "elasticsearch",
            "document.upserted",
            "RAG orchestrator upserted a top-level Elasticsearch document by explicit id.",
            index=index,
            document_id=document_id,
        )

    async def get_document(self, index: str, document_id: str) -> Dict[str, Any] | None:
        response = await self._client.get(f"/{index}/_doc/{document_id}")
        if response.status_code == 404:
            log_flow(
                "elasticsearch",
                "document.miss",
                "Elasticsearch did not contain the requested document id.",
                index=index,
                document_id=document_id,
            )
            return None
        response.raise_for_status()
        payload = response.json()
        log_flow(
            "elasticsearch",
            "document.hit",
            "Elasticsearch returned the requested document by id.",
            index=index,
            document_id=document_id,
        )
        return payload.get("_source")

    async def search(self, index: str, query: Dict[str, Any], size: int = 100) -> list[Dict[str, Any]]:
        body = {"query": query, "size": size, "sort": [{"created_at": {"order": "asc"}}]}
        response = await self._client.post(f"/{index}/_search", json=body)
        response.raise_for_status()
        payload = response.json()
        results: list[Dict[str, Any]] = []
        for hit in payload.get("hits", {}).get("hits", []):
            source = hit.get("_source")
            if source:
                results.append(source)
        log_flow(
            "elasticsearch",
            "search.completed",
            "Elasticsearch completed a document search request for the orchestrator.",
            index=index,
            size=size,
            result_count=len(results),
        )
        return results
