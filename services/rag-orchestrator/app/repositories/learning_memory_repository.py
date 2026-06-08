from __future__ import annotations

"""Persistence adapter for learning-flow writes to Elasticsearch.

The workflow service talks to this repository instead of calling the raw
Elasticsearch client directly. That keeps index names and storage concerns out
of the higher-level learning logic.
"""

from typing import Any, Mapping

from ..clients.elasticsearch_client import ElasticsearchClient


class LearningMemoryRepository:
    """Store learning artifacts in the Elasticsearch indices used by RAG flows."""

    def __init__(
        self,
        elasticsearch_client: ElasticsearchClient,
        indices: Mapping[str, str],
    ) -> None:
        """Bind the low-level client with the configured logical index names."""
        self._elasticsearch_client = elasticsearch_client
        self._indices = indices

    async def store_interaction(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        turn: int,
        metadata: dict[str, Any] | None,
        phase: str | None,
        embedding: list[float] | None = None,
    ) -> None:
        """Persist one transcript turn into the session interaction index."""
        await self._elasticsearch_client.store_interaction(
            index=self._indices["session_interactions"],
            session_id=session_id,
            role=role,
            content=content,
            turn=turn,
            embedding=embedding,
            metadata=metadata,
            phase=phase,
        )

    async def store_snapshot(
        self,
        *,
        session_id: str,
        snapshot: dict[str, Any],
        embedding: list[float] | None = None,
    ) -> None:
        """Persist a calibration or learning snapshot for later retrieval."""
        await self._elasticsearch_client.store_snapshot(
            index=self._indices["knowledge_snapshots"],
            session_id=session_id,
            snapshot=snapshot,
            embedding=embedding,
        )

    async def store_dependency_node(self, *, node: dict[str, Any]) -> None:
        """Persist one roadmap node into the dependency graph index."""
        await self._elasticsearch_client.store_dependency_node(
            index=self._indices["dependency_graph"],
            node=node,
        )

    async def store_learning_resource(
        self,
        *,
        resource: dict[str, Any],
        embedding: list[float] | None = None,
    ) -> None:
        """Persist one learning resource, optionally with an embedding vector."""
        await self._elasticsearch_client.store_learning_resource(
            index=self._indices["learning_resources"],
            resource=resource,
            embedding=embedding,
        )

    async def upsert_user_profile(
        self,
        *,
        session_id: str,
        goal: str,
        experience_summary: str,
        knowledge_vector: list[float] | None = None,
    ) -> None:
        """Create or update the learner profile document for the active session."""
        await self._elasticsearch_client.upsert_user_profile(
            index=self._indices["user_profiles"],
            document_id=session_id,
            goal=goal,
            experience_summary=experience_summary,
            knowledge_vector=knowledge_vector,
        )
