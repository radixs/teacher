from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import httpx


@dataclass
class DuckDuckGoClient:
    base_url: str = "https://duckduckgo.com/html/"
    user_agent: str = "teacher-app-bot/0.1"
    timeout: float = 15.0

    async def search(self, query: str) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": self.user_agent,
        }
        params = {"q": query}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return parse_results(response.text)


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
