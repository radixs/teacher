from __future__ import annotations

from fastapi import FastAPI

from .api.routes import sessions
from .core.config import get_settings
from .core.dependencies import (
    get_embedding_client,
    get_llm_client,
    get_search_client,
)

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(sessions.router, prefix="/v1")


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event() -> None:
    # Touch dependencies so they're ready to use and to surface misconfiguration early.
    _ = get_llm_client()
    _ = get_embedding_client()
    _ = get_search_client()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await get_llm_client().close()
    await get_embedding_client().close()
    await get_search_client().close()
