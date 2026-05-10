from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from ..clients.duckduckgo import DuckDuckGoClient
from ..config import Settings, get_settings
from ..flow_logger import log_flow
from ..scrapers.simple import WebScraper

router = APIRouter(prefix="/search", tags=["search"])

def get_duckduckgo_client(settings: Settings = Depends(get_settings)) -> DuckDuckGoClient:
    return DuckDuckGoClient(user_agent=settings.user_agent)

def get_scraper(settings: Settings = Depends(get_settings)) -> WebScraper:
    return WebScraper(user_agent=settings.user_agent)


@router.get("")
async def search(
    q: str = Query(..., min_length=2, max_length=512),
    enrich: bool = Query(False),
    duckduckgo: DuckDuckGoClient = Depends(get_duckduckgo_client),
    scraper: WebScraper = Depends(get_scraper),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    log_flow(
        "search-agent",
        "search.received",
        "Search agent received a search request.",
        query=q,
        enrich=enrich,
    )
    try:
        results = await duckduckgo.search(q)
    except Exception as exc:
        log_flow(
            "search-agent",
            "search.failed",
            "Search agent failed while calling DuckDuckGo.",
            query=q,
            error=str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    enriched: List[Dict[str, Any]] = []
    if enrich:
        for result in results[:3]:
            try:
                enriched_content = await scraper.fetch(result["url"])
                enriched.append({**result, **enriched_content})
                await asyncio.sleep(settings.request_interval_seconds)
            except Exception:
                log_flow(
                    "search-agent",
                    "search.enrich_skipped",
                    "Search agent could not enrich one result page and kept the base result instead.",
                    url=result.get("url"),
                )
                enriched.append(result)
    else:
        enriched = results

    log_flow(
        "search-agent",
        "search.completed",
        "Search agent returned search results to the caller.",
        query=q,
        result_count=len(enriched),
        enrich=enrich,
    )
    return {"query": q, "results": enriched}
