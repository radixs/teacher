from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import httpx
from readability import Document


@dataclass
class WebScraper:
    user_agent: str = "teacher-app-bot/0.1"
    timeout: float = 15.0

    async def fetch(self, url: str) -> Dict[str, Any]:
        headers = {"User-Agent": self.user_agent}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        doc = Document(html)
        return {
            "title": doc.short_title(),
            "content": doc.summary(html_partial=True),
        }
