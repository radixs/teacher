from __future__ import annotations

from typing import Any, Dict

import httpx


class LlmClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)

    async def generate(self, prompt: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        # TODO: integrate with llama.cpp server once available.
        _ = context  # placeholder until real payload defined
        payload: Dict[str, Any] = {"prompt": prompt}
        if context:
            payload["context"] = context
        try:
            response = await self._client.post("/completion", json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data
            return {"text": str(data)}
        except Exception:
            return {
                "text": "This is a placeholder response from the orchestrator until the LLM service is ready.",
            }

    async def close(self) -> None:
        await self._client.aclose()
