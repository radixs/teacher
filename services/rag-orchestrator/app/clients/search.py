from __future__ import annotations

import re
from typing import Any, Dict

import httpx

from ..core.flow_logger import log_flow

MAX_QUERY_LENGTH = 320


class SearchClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def search(self, query: str, *, enrich: bool = False) -> Dict[str, Any]:
        normalized_query = self._normalize_query(query)
        if normalized_query != query:
            log_flow(
                "search-agent",
                "search.query_truncated",
                "RAG orchestrator shortened the external search query to fit the search-agent request budget.",
                original_length=len(query),
                truncated_length=len(normalized_query),
            )
        log_flow(
            "search-agent",
            "search.requested",
            "RAG orchestrator requested external search results from the search agent.",
            query=normalized_query,
            enrich=enrich,
        )
        try:
            response = await self._client.get("/v1/search", params={"q": normalized_query, "enrich": enrich})
            response.raise_for_status()
            payload = response.json()
            log_flow(
                "search-agent",
                "search.received",
                "RAG orchestrator received search results from the search agent.",
                query=normalized_query,
                result_count=len(payload.get("results", [])),
                enrich=enrich,
            )
            return payload
        except Exception as exc:
            log_flow(
                "search-agent",
                "search.fallback",
                "Search request failed, so the orchestrator continued with no external results.",
                query=normalized_query,
                enrich=enrich,
                error=str(exc),
            )
            return {"results": []}

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _normalize_query(query: str) -> str:
        collapsed = re.sub(r"\s+", " ", query).strip()
        if len(collapsed) <= MAX_QUERY_LENGTH:
            return collapsed

        truncated = collapsed[:MAX_QUERY_LENGTH].rstrip()
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return truncated.strip()
