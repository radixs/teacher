from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import httpx


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

    async def store_dependency_node(self, index: str, node: Dict[str, Any]) -> None:
        payload = dict(node)
        payload.setdefault("created_at", datetime.utcnow().isoformat())
        await self._client.post(f"/{index}/_doc", json=payload)

    async def close(self) -> None:
        await self._client.aclose()

    async def upsert_document(self, index: str, document_id: str, document: Dict[str, Any]) -> None:
        await self._client.put(f"/{index}/_doc/{document_id}", json=document)

    async def get_document(self, index: str, document_id: str) -> Dict[str, Any] | None:
        response = await self._client.get(f"/{index}/_doc/{document_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
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
        return results
