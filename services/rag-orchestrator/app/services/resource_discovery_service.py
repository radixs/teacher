from __future__ import annotations

import html
import re
from typing import Any

from ..clients.embedding_client import EmbeddingClient
from ..clients.search_client import SearchClient
from ..core.flow_logger import log_flow
from ..repositories.learning_memory_repository import LearningMemoryRepository


class ResourceDiscoveryService:
    """Coordinate external resource discovery for tuning and learning flows."""

    def __init__(
        self,
        *,
        search_client: SearchClient,
        embedding_client: EmbeddingClient,
        learning_memory_repository: LearningMemoryRepository,
    ) -> None:
        self._search_client = search_client
        self._embedding_client = embedding_client
        self._learning_memory_repository = learning_memory_repository

    async def discover_resources(
        self,
        *,
        session_id: str,
        query: str,
        enrich: bool = False,
        extra_tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        search_response = await self._search_client.search(query, enrich=enrich)
        resources = self._normalize_search_results(search_response)
        log_flow(
            "rag-orchestrator",
            "search.resources.selected",
            "RAG orchestrator selected external search results for roadmap generation without inline page scraping to keep the learner request responsive.",
            session_id=session_id,
            search_query=query,
            external_resources=len(resources),
        )
        await self.persist_resources(
            session_id=session_id,
            resources=resources,
            extra_tags=extra_tags,
        )
        return resources

    async def persist_resources(
        self,
        *,
        session_id: str,
        resources: list[dict[str, Any]],
        concept_id: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> None:
        seen_urls: set[str] = set()
        for resource in resources:
            title = str(resource.get("title") or "").strip()
            url = str(resource.get("url") or "").strip()
            if not title or not url or url in seen_urls:
                continue

            seen_urls.add(url)
            summary = self._clean_text(resource.get("summary") or "")
            content = self._clean_text(resource.get("content") or "")
            snippet = self._clean_text(resource.get("snippet") or summary)
            resource_text = "\n".join(part for part in [title, summary, content] if part)
            embedding = await self._embedding_client.embed(resource_text) if resource_text else []
            tags = [
                tag for tag in (extra_tags or []) if isinstance(tag, str) and tag.strip()
            ]
            await self._learning_memory_repository.store_learning_resource(
                resource={
                    "title": title,
                    "url": url,
                    "source": resource.get("source", "generated"),
                    "type": resource.get("type", "reference"),
                    "summary": summary,
                    "content": content,
                    "snippet": snippet,
                    "tags": list(dict.fromkeys(tags)),
                    "session_id": session_id,
                    "concept_id": concept_id,
                },
                embedding=embedding or None,
            )

    @staticmethod
    def _clean_text(value: str | None) -> str:
        if not value:
            return ""
        without_tags = re.sub(r"<[^>]+>", " ", value)
        normalized = re.sub(r"\s+", " ", html.unescape(without_tags))
        return normalized.strip()

    @classmethod
    def _normalize_search_results(
        cls,
        search_response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        for result in search_response.get("results", []) or []:
            if not isinstance(result, dict):
                continue
            title = str(result.get("title") or "").strip()
            url = str(result.get("url") or "").strip()
            if not title or not url:
                continue
            resources.append(
                {
                    "title": title,
                    "url": url,
                    "summary": cls._clean_text(
                        result.get("snippet") or result.get("content") or ""
                    ),
                    "content": cls._clean_text(result.get("content") or ""),
                    "snippet": cls._clean_text(result.get("snippet") or ""),
                    "type": str(result.get("type") or "search_result"),
                    "source": "duckduckgo",
                }
            )
        return resources
