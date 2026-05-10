from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import httpx

from ..flow_logger import log_flow

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class DuckDuckGoClient:
    base_url: str = "https://html.duckduckgo.com/html/"
    user_agent: str = BROWSER_USER_AGENT
    timeout: float = 15.0

    async def search(self, query: str) -> List[Dict[str, Any]]:
        user_agent = self._effective_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        params = {"q": query}
        log_flow(
            "search-agent",
            "duckduckgo.requested",
            "Search agent is querying the DuckDuckGo HTML endpoint.",
            query=query,
            user_agent=user_agent,
        )
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=headers,
            follow_redirects=True,
        ) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            results = parse_results(response.text)
            log_flow(
                "search-agent",
                "duckduckgo.completed",
                "Search agent parsed results returned by DuckDuckGo.",
                query=query,
                result_count=len(results),
            )
            return results

    def _effective_user_agent(self) -> str:
        normalized = (self.user_agent or "").strip()
        if not normalized or normalized.startswith("teacher-app-bot/"):
            return BROWSER_USER_AGENT
        return normalized


def parse_results(html: str) -> List[Dict[str, Any]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Any]] = []
    for result in soup.select(".result"):
        link = result.select_one("a.result__a")
        snippet = result.select_one("a.result__snippet")
        if not link:
            continue
        results.append(
            {
                "title": link.get_text(strip=True),
                "url": link["href"],
                "snippet": snippet.get_text(strip=True) if snippet else "",
            }
        )
    return results
