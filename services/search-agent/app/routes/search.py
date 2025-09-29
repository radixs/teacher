from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from ..clients.duckduckgo import DuckDuckGoClient
from ..config import Settings, get_settings
from ..scrapers.simple import WebScraper

router = APIRouter(prefix="/search", tags=["search"])

def get_duckduckgo_client(settings: Settings = Depends(get_settings)) -> DuckDuckGoClient:
    return DuckDuckGoClient(user_agent=settings.user_agent)

def get_scraper(settings: Settings = Depends(get_settings)) -> WebScraper:
    return WebScraper(user_agent=settings.user_agent)


@router.get("")
async def search(
    q: str = Query(..., min_length=2, max_length=256),
    enrich: bool = Query(False),
    duckduckgo: DuckDuckGoClient = Depends(get_duckduckgo_client),
    scraper: WebScraper = Depends(get_scraper),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    try:
        results = await duckduckgo.search(q)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    enriched: List[Dict[str, Any]] = []
    if enrich:
        for result in results[:3]:
            try:
                enriched_content = await scraper.fetch(result["url"])
                enriched.append({**result, **enriched_content})
                await asyncio.sleep(settings.request_interval_seconds)
            except Exception:
                enriched.append(result)
    else:
        enriched = results

    return {"query": q, "results": enriched}
