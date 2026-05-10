from __future__ import annotations

from typing import Any, Dict, List

import httpx

from ..core.flow_logger import log_flow


class EmbeddingClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def embed(self, text: str) -> List[float]:
        log_flow(
            "embedding-worker",
            "embed.requested",
            "RAG orchestrator requested an embedding for learner text.",
            text=text,
            text_length=len(text),
        )
        try:
            response = await self._client.post("/embed", json={"text": text})
            response.raise_for_status()
            payload: Dict[str, Any] = response.json()
            vector = payload.get("embedding", [])
            log_flow(
                "embedding-worker",
                "embed.received",
                "RAG orchestrator received an embedding vector from the embedding worker.",
                dimensions=len(vector),
                model=payload.get("model"),
            )
            return vector
        except Exception as exc:
            log_flow(
                "embedding-worker",
                "embed.fallback",
                "Embedding request failed, so the orchestrator continued with an empty vector.",
                text_length=len(text),
                error=str(exc),
            )
            return []

    async def close(self) -> None:
        await self._client.aclose()
