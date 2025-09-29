from __future__ import annotations

from typing import Any, Dict, List

import httpx


class EmbeddingClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def embed(self, text: str) -> List[float]:
        try:
            response = await self._client.post("/embed", json={"text": text})
            response.raise_for_status()
            payload: Dict[str, Any] = response.json()
            return payload.get("embedding", [])
        except Exception:
            return []

    async def close(self) -> None:
        await self._client.aclose()
