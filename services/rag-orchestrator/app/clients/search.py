from __future__ import annotations

from typing import Any, Dict

import httpx


class SearchClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def search(self, query: str) -> Dict[str, Any]:
        try:
            response = await self._client.get("/search", params={"q": query})
            response.raise_for_status()
            return response.json()
        except Exception:
            return {"results": []}

    async def close(self) -> None:
        await self._client.aclose()
