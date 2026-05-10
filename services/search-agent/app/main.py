from __future__ import annotations

from fastapi import FastAPI

from .flow_logger import log_flow
from .routes import search

app = FastAPI(title="Search Agent", version="0.1.0")
app.include_router(search.router, prefix="/v1")


@app.on_event("startup")
async def startup() -> None:
    log_flow(
        "search-agent",
        "startup.completed",
        "Search agent started and is ready to query DuckDuckGo or scrape result pages.",
    )


@app.get("/health")
async def health() -> dict[str, str]:
    log_flow(
        "search-agent",
        "health.checked",
        "Search agent health endpoint was called.",
    )
    return {"status": "ok"}
