from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import httpx
from readability import Document

from ..flow_logger import log_flow

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class WebScraper:
    user_agent: str = BROWSER_USER_AGENT
    timeout: float = 15.0

    async def fetch(self, url: str) -> Dict[str, Any]:
        headers = {"User-Agent": self._effective_user_agent()}
        log_flow(
            "search-agent",
            "scraper.requested",
            "Search agent started fetching a result page for enrichment.",
            url=url,
        )
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        doc = Document(html)
        payload = {
            "title": doc.short_title(),
            "content": doc.summary(html_partial=True),
        }
        log_flow(
            "search-agent",
            "scraper.completed",
            "Search agent extracted readable content from a fetched result page.",
            url=url,
            title=payload["title"],
        )
        return payload

    def _effective_user_agent(self) -> str:
        normalized = (self.user_agent or "").strip()
        if not normalized or normalized.startswith("teacher-app-bot/"):
            return BROWSER_USER_AGENT
        return normalized
